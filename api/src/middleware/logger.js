/**
 * Request Logging Middleware
 * Logs all incoming requests with timing and sanitizes sensitive data
 */

const LOG_LEVELS = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3,
  trace: 4,
};

function getLevelValue(level) {
  return LOG_LEVELS[level] ?? LOG_LEVELS.info;
}

function shouldLog(level) {
  const envLevel = process.env.LOG_LEVEL || 'info';
  return getLevelValue(level) <= getLevelValue(envLevel);
}

function sanitize(obj, fields = ['password', 'token', 'authorization', 'secret', 'apiKey', 'access_token']) {
  if (!obj) return obj;
  const sanitized = Array.isArray(obj) ? [...obj] : { ...obj };

  for (const field of fields) {
    if (sanitized[field]) {
      sanitized[field] = '***REDACTED***';
    }
  }

  return sanitized;
}

function formatResponse(res) {
  const headers = {};
  res.getHeaderNames().forEach((name) => {
    headers[name] = res.getHeader(name);
  });
  return headers;
}

function formatRequest(req) {
  return {
    method: req.method,
    url: req.originalUrl || req.url,
    headers: sanitize(req.headers),
    ip: req.ip || req.connection?.remoteAddress,
    query: req.query,
    params: req.params,
    body: req.body ? sanitize(req.body) : undefined,
  };
}

function loggerMiddleware(req, res, next) {
  if (!shouldLog('debug')) {
    return next();
  }

  const startTime = Date.now();
  const requestId = req.headers['x-request-id'] || `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  // Attach request ID to request for correlation
  req.requestId = requestId;

  // Log incoming request
  const requestInfo = formatRequest(req);

  console.log('\n┌─ INCOMING REQUEST ─────────────────────────────────────────');
  console.log(`│ [${new Date().toISOString()}] [${requestId}]`);
  console.log(`│ ${requestInfo.method} ${requestInfo.url}`);
  console.log(`│ IP: ${requestInfo.ip}`);
  if (shouldLog('trace') && requestInfo.body) {
    console.log(`│ Body: ${JSON.stringify(requestInfo.body, null, 2)}`);
  }
  console.log('└───────────────────────────────────────────────────────────');

  // Capture response data
  const originalSend = res.send;
  const originalJson = res.json;

  let responseBody;

  res.send = function (body) {
    responseBody = body;
    return originalSend.apply(this, arguments);
  };

  res.json = function (body) {
    responseBody = body;
    return originalJson.apply(this, arguments);
  };

  // Log when response is finished
  res.on('finish', () => {
    const duration = Date.now() - startTime;
    const statusIcon = res.statusCode >= 400 ? '❌' : res.statusCode >= 300 ? '⚠️' : '✅';

    console.log(`┌─ OUTGOING RESPONSE ${statusIcon}─────────────────────────────────────`);
    console.log(`│ [${new Date().toISOString()}] [${requestId}]`);
    console.log(`│ ${requestInfo.method} ${requestInfo.url}`);
    console.log(`│ Status: ${res.statusCode} ${res.statusMessage || ''} (${duration}ms)`);

    if (shouldLog('trace') && responseBody) {
      try {
        const parsed = typeof responseBody === 'string' ? JSON.parse(responseBody) : responseBody;
        console.log(`│ Body: ${JSON.stringify(sanitize(parsed), null, 2)}`);
      } catch {
        console.log(`│ Body: ${responseBody}`);
      }
    }

    console.log('└───────────────────────────────────────────────────────────\n');
  });

  next();
}

/**
 * Error logging middleware
 */
function errorLogger(err, req, res, next) {
  const requestId = req.requestId || `err-${Date.now()}`;

  console.error('\n┌─ ERROR ❌────────────────────────────────────────────────');
  console.error(`│ [${new Date().toISOString()}] [${requestId}]`);
  console.error(`│ ${req.method} ${req.url}`);
  console.error(`│ Error: ${err.message}`);
  console.error(`│ Stack: ${err.stack}`);
  console.error('└───────────────────────────────────────────────────────────');

  res.status(500).json({
    error: 'Internal Server Error',
    requestId,
    message: process.env.NODE_ENV === 'development' ? err.message : undefined,
  });
}

/**
 * Request ID middleware - adds unique ID to each request
 */
function requestIdMiddleware(req, res, next) {
  const requestId = req.headers['x-request-id'] || `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  req.requestId = requestId;
  res.setHeader('X-Request-ID', requestId);
  next();
}

module.exports = {
  loggerMiddleware,
  errorLogger,
  requestIdMiddleware,
};
