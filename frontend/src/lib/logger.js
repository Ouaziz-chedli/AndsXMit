/**
 * Professional Logger Utility
 * Supports log levels, namespaces, timestamps, and debug mode
 */

const LOG_LEVELS = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3,
  trace: 4,
};

const currentLevel = import.meta.env.VITE_LOG_LEVEL || 'debug';
const isDebugMode = import.meta.env.VITE_DEBUG === 'true';

function getLevelValue(level) {
  return LOG_LEVELS[level] ?? LOG_LEVELS.info;
}

function shouldLog(level) {
  if (!isDebugMode && level === 'debug') return false;
  return getLevelValue(level) <= getLevelValue(currentLevel);
}

function formatMessage(level, namespace, message, data) {
  const timestamp = new Date().toISOString();
  const prefix = data ? `[${timestamp}] [${level.toUpperCase()}] [${namespace}]` : `[${timestamp}] [${level.toUpperCase()}] [${namespace}]`;

  if (data) {
    return `${prefix} ${message} ${JSON.stringify(data, null, 2)}`;
  }
  return `${prefix} ${message}`;
}

const logger = {
  error(namespace, message, data) {
    if (shouldLog('error')) {
      console.error(formatMessage('error', namespace, message, data));
    }
  },

  warn(namespace, message, data) {
    if (shouldLog('warn')) {
      console.warn(formatMessage('warn', namespace, message, data));
    }
  },

  info(namespace, message, data) {
    if (shouldLog('info')) {
      console.info(formatMessage('info', namespace, message, data));
    }
  },

  debug(namespace, message, data) {
    if (shouldLog('debug')) {
      console.debug(formatMessage('debug', namespace, message, data));
    }
  },

  trace(namespace, message, data) {
    if (shouldLog('trace')) {
      console.trace(formatMessage('trace', namespace, message, data));
    }
  },

  group(label) {
    if (isDebugMode) {
      console.group(`[${label}]`);
    }
  },

  groupEnd() {
    if (isDebugMode) {
      console.groupEnd();
    }
  },

  table(data) {
    if (isDebugMode) {
      console.table(data);
    }
  },

  /**
   * Log API request with timing
   */
  logRequest(namespace, method, url, headers, body) {
    if (!isDebugMode) return;

    const safeBody = sanitizeForLogging(body);
    const safeHeaders = sanitizeForLogging(headers);

    console.log(`┌─ API REQUEST ────────────────────────────────────────────`);
    console.log(`│ [${new Date().toISOString()}] [${namespace}]`);
    console.log(`│ ${method} ${url}`);
    if (safeHeaders) {
      console.log(`│ Headers: ${JSON.stringify(safeHeaders, null, 2)}`);
    }
    if (safeBody) {
      console.log(`│ Body: ${JSON.stringify(safeBody, null, 2)}`);
    }
    console.log(`└───────────────────────────────────────────────────────────`);
  },

  /**
   * Log API response with timing
   */
  logResponse(namespace, method, url, status, statusText, headers, body, duration) {
    const level = status >= 400 ? 'error' : status >= 300 ? 'warn' : 'debug';

    const safeBody = sanitizeForLogging(body);
    const safeHeaders = sanitizeForLogging(headers);

    const statusColor = status >= 400 ? '❌' : status >= 300 ? '⚠️' : '✅';
    const durationStr = duration ? ` (${duration}ms)` : '';

    console.log(`┌─ API RESPONSE ${statusColor}──────────────────────────────────────────`);
    console.log(`│ [${new Date().toISOString()}] [${namespace}]`);
    console.log(`│ ${method} ${url}`);
    console.log(`│ Status: ${status} ${statusText}${durationStr}`);
    if (safeHeaders) {
      console.log(`│ Headers: ${JSON.stringify(safeHeaders, null, 2)}`);
    }
    if (safeBody) {
      console.log(`│ Body: ${JSON.stringify(safeBody, null, 2)}`);
    }
    console.log(`└───────────────────────────────────────────────────────────`);
  },

  /**
   * Log network error
   */
  logNetworkError(namespace, method, url, error) {
    console.error(`┌─ NETWORK ERROR ❌─────────────────────────────────────────`);
    console.error(`│ [${new Date().toISOString()}] [${namespace}]`);
    console.error(`│ ${method} ${url}`);
    console.error(`│ Error: ${error.message || error}`);
    if (error.stack) {
      console.error(`│ Stack: ${error.stack}`);
    }
    console.error(`└───────────────────────────────────────────────────────────`);
  },
};

/**
 * Sanitize sensitive data from logs
 */
function sanitizeForLogging(obj) {
  if (!obj) return obj;
  const sanitized = { ...obj };
  const sensitiveFields = ['password', 'token', 'access_token', 'authorization', 'secret', 'apiKey', 'api_key'];

  for (const field of sensitiveFields) {
    if (sanitized[field]) {
      sanitized[field] = '***REDACTED***';
    }
  }

  return sanitized;
}

export default logger;
export { logger };
