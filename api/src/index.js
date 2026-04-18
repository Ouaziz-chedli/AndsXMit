const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { createProxyMiddleware } = require('http-proxy-middleware');
const authRoutes = require('./routes/auth.js');
const userRoutes = require('./routes/user.js');

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json());

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

app.use(
  '/api/llm',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathRewrite: (path) => `/api/llm${path}`,
  })
);

app.use(
  '/api/rag',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathRewrite: (path) => `/api/rag${path}`,
  })
);

// General Error Handler
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ detail: 'Something broke!' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running securely on port ${PORT}`);
});
