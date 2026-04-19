const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { createProxyMiddleware } = require('http-proxy-middleware');
const http = require('http');
const { loggerMiddleware, errorLogger, requestIdMiddleware } = require('./middleware/logger');
const authRoutes = require('./routes/auth.js');
const userRoutes = require('./routes/user.js');

dotenv.config();

const app = express();

// Request ID for all requests
app.use(requestIdMiddleware);

// CORS
app.use(cors());

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Request logging (skip health checks)
app.use((req, res, next) => {
  if (req.path === '/health' || req.path === '/api/health') {
    return next();
  }
  loggerMiddleware(req, res, next);
});

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/user', userRoutes);

// Proxy configuration for Python Backend
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
app.use(
  '/api/v1',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathRewrite: (path) => `/api/v1${path}`,
    onProxyReq: (proxyReq, req) => {
      if (process.env.DEBUG === 'true') {
        console.log(`[PROXY] ${req.method} ${req.originalUrl} -> ${BACKEND_URL}${proxyReq.path}`);
      }
      // Pass request ID to backend
      if (req.requestId) {
        proxyReq.setHeader('X-Request-ID', req.requestId);
      }
    },
    onProxyRes: (proxyRes, req) => {
      if (process.env.DEBUG === 'true') {
        console.log(`[PROXY] Response ${proxyRes.statusCode} for ${req.method} ${req.originalUrl}`);
      }
    },
    onError: (err, req, res) => {
      console.error(`[PROXY] Error: ${err.message}`);
      res.status(502).json({ error: 'Proxy error', detail: err.message });
    },
  })
);

// Expose backend health endpoint through the API gateway.
app.use(
  '/api/health',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathRewrite: () => '/health',
  })
);

// LLM Chat endpoint - direct handler to avoid http-proxy-middleware issues
// with FastAPI's async responses
app.post('/api/llm/chat', async (req, res) => {
  const requestId = req.requestId || `req-${Date.now()}`;
  const startTime = Date.now();

  console.log(`[LLM-DIRECT] ${req.method} /api/llm/chat - requestId: ${requestId}`);

  // req.body should be parsed by express.json() middleware
  const parsedBody = req.body || {};
  console.log(`[LLM-DIRECT] Body keys: ${Object.keys(parsedBody).join(', ')}`);

  const data = JSON.stringify(parsedBody);
  const options = {
    hostname: 'backend',
    port: 8000,
    path: '/api/llm/chat',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(data),
      'X-Request-ID': requestId,
      'X-Forwarded-For': req.ip,
      'Connection': 'close',
    },
    agent: false,  // Disable connection pooling to avoid socket issues
  };

  console.log(`[LLM-DIRECT] Forwarding to ${BACKEND_URL}/api/llm/chat, body size: ${Buffer.byteLength(data)} bytes`);

  const proxyReq = http.request(options, (proxyRes) => {
    console.log(`[LLM-DIRECT] Backend response: ${proxyRes.statusCode} in ${Date.now() - startTime}ms`);

    // Collect response data
    const chunks = [];
    proxyRes.on('data', (chunk) => {
      chunks.push(chunk);
    });
    proxyRes.on('end', () => {
      const body = Buffer.concat(chunks).toString();
      console.log(`[LLM-DIRECT] Response complete: ${body.length} chars in ${Date.now() - startTime}ms`);
      try {
        const parsed = JSON.parse(body);
        res.status(proxyRes.statusCode).json(parsed);
      } catch (e) {
        res.status(proxyRes.statusCode).send(body);
      }
    });
  });

  proxyReq.on('error', (err) => {
    console.error(`[LLM-DIRECT] Error: ${err.message} after ${Date.now() - startTime}ms`);
    res.status(502).json({ error: 'Proxy error', detail: err.message });
  });

  proxyReq.on('timeout', () => {
    console.error(`[LLM-DIRECT] Request timeout after ${Date.now() - startTime}ms`);
    proxyReq.destroy();
    res.status(504).json({ error: 'Gateway timeout', detail: 'Backend did not respond in time' });
  });

  proxyReq.setTimeout(120000);  // 120 second timeout for MedGemma

  proxyReq.write(data);
  proxyReq.end();

  console.log(`[LLM-DIRECT] Request sent, waiting for response...`);
});

app.use(
  '/api/rag',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathRewrite: (path) => {
      // /api/rag/upload-context -> /api/v1/documents/upload
      if (path === '/api/rag/upload-context') {
        return '/api/v1/documents/upload';
      }
      // /api/rag/search -> /api/v1/documents/search
      if (path.startsWith('/api/rag/search')) {
        return path.replace('/api/rag/search', '/api/v1/documents/search');
      }
      // Default: passthrough
      return path;
    },
    onProxyReq: (proxyReq, req) => {
      if (process.env.DEBUG === 'true') {
        console.log(`[PROXY] ${req.method} ${req.originalUrl} -> ${BACKEND_URL}${proxyReq.path}`);
      }
      if (req.requestId) {
        proxyReq.setHeader('X-Request-ID', req.requestId);
      }
    },
    onProxyRes: (proxyRes, req) => {
      if (process.env.DEBUG === 'true') {
        console.log(`[PROXY] Response ${proxyRes.statusCode} for ${req.method} ${req.originalUrl}`);
      }
    },
    onError: (err, req, res) => {
      console.error(`[PROXY] Error: ${err.message}`);
      res.status(502).json({ error: 'Proxy error', detail: err.message });
    },
  })
);

// Debug endpoint - returns environment info
app.get('/api/debug', (req, res) => {
  if (process.env.NODE_ENV === 'production') {
    return res.status(404).json({ error: 'Not found' });
  }

  res.json({
    environment: process.env.NODE_ENV || 'development',
    debug: process.env.DEBUG === 'true',
    logLevel: process.env.LOG_LEVEL || 'info',
    timestamp: new Date().toISOString(),
    requestId: req.requestId,
    uptime: process.uptime(),
    memory: process.memoryUsage(),
  });
});

// General Error Handler - must be last
app.use(errorLogger);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`\n🚀 Server running on port ${PORT}`);
  console.log(`   Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`   Debug: ${process.env.DEBUG === 'true' ? 'ON' : 'OFF'}`);
  console.log(`   Backend URL: ${BACKEND_URL}`);
  console.log(`   Log Level: ${process.env.LOG_LEVEL || 'info'}`);
  console.log(`   LLM Proxy mount: /api/llm -> ${BACKEND_URL}/api/llm`);
  console.log(`   V1 Proxy mount: /api/v1 -> ${BACKEND_URL}/api/v1\n`);
});
