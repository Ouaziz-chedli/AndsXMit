/**
 * API Client with automatic request/response logging
 * Wraps fetch with timing, error handling, and debug output
 */

import logger from './logger';

const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');
const NAMESPACE = 'ApiClient';
const isDebugMode = import.meta.env.VITE_DEBUG === 'true';

/**
 * Emit log event for DebugPanel
 */
function emitLog(logData) {
  if (isDebugMode) {
    window.dispatchEvent(new CustomEvent('api-log', { detail: logData }));
  }
}

/**
 * Build full URL from path
 */
export function buildApiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  // If we have a base URL and the path is absolute, use just the path
  if (API_BASE_URL) {
    return `${API_BASE_URL}${normalizedPath}`;
  }

  // Otherwise return relative path (for Vite proxy)
  return normalizedPath;
}

/**
 * Generic API request function with logging
 */
async function apiRequest(method, path, options = {}) {
  const url = buildApiUrl(path);
  const startTime = performance.now();

  const {
    body,
    headers = {},
    signal,
    ...rest
  } = options;

  // Build final headers
  const finalHeaders = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // Emit request log
  emitLog({
    type: 'request',
    method,
    url,
    headers: finalHeaders,
    body,
    timestamp: new Date().toISOString(),
  });

  try {
    const response = await fetch(url, {
      method,
      headers: finalHeaders,
      body: body ? JSON.stringify(body) : undefined,
      signal,
      ...rest,
    });

    const duration = Math.round(performance.now() - startTime);

    // Parse response
    let responseData;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      responseData = await response.json();
    } else {
      responseData = await response.text();
    }

    // Emit response log
    emitLog({
      type: 'response',
      method,
      url,
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
      body: responseData,
      duration,
      timestamp: new Date().toISOString(),
    });

    return {
      ok: response.ok,
      status: response.status,
      statusText: response.statusText,
      data: responseData,
      headers: Object.fromEntries(response.headers.entries()),
      duration,
    };
  } catch (error) {
    const duration = Math.round(performance.now() - startTime);

    // Emit error log
    emitLog({
      type: 'error',
      method,
      url,
      error: error.message,
      duration,
      timestamp: new Date().toISOString(),
    });

    return {
      ok: false,
      status: 0,
      statusText: 'Network Error',
      data: null,
      error: error.message || 'Network request failed',
      duration,
    };
  }
}

/**
 * API client object with methods for each HTTP verb
 */
export const apiClient = {
  get(path, options = {}) {
    return apiRequest('GET', path, options);
  },

  post(path, body, options = {}) {
    return apiRequest('POST', path, { ...options, body });
  },

  put(path, body, options = {}) {
    return apiRequest('PUT', path, { ...options, body });
  },

  patch(path, body, options = {}) {
    return apiRequest('PATCH', path, { ...options, body });
  },

  delete(path, options = {}) {
    return apiRequest('DELETE', path, options);
  },

  /**
   * Upload file with progress tracking
   */
  async uploadFile(path, file, onProgress) {
    const url = buildApiUrl(path);
    const startTime = performance.now();

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      });

      xhr.addEventListener('load', () => {
        const duration = Math.round(performance.now() - startTime);

        try {
          const data = JSON.parse(xhr.responseText);
          logger.logResponse(NAMESPACE, 'POST', url, xhr.status, xhr.statusText, {}, data, duration);
          resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, data, duration });
        } catch {
          resolve({ ok: false, status: xhr.status, data: xhr.responseText, duration });
        }
      });

      xhr.addEventListener('error', (error) => {
        logger.logNetworkError(NAMESPACE, 'POST', url, error);
        reject(error);
      });

      logger.logRequest(NAMESPACE, 'POST', url, { 'Content-Type': file.type }, { name: file.name, size: file.size });

      xhr.open('POST', url);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });
  },
};

export default apiClient;
