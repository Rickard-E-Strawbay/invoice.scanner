/**
 * API utility for centralized API URL management
 */

// Determine API URL - try env var first, then fallback to smart detection
export const API_BASE_URL = (() => {
  // 1. Check explicit VITE_API_URL environment variable (set by docker-compose or pipeline)
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && envUrl.trim() !== '') {
    console.log('✅ Using explicit API URL from environment:', envUrl);
    return envUrl;
  }
  
  // 2. Fallback: Smart detection based on hostname
  const hostname = window.location.hostname || 'localhost';
  const protocol = window.location.protocol;
  
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    // Local development: use localhost:5001
    const fallbackUrl = `${protocol}//localhost:5001`;
    console.log('✅ Local development detected, using:', fallbackUrl);
    return fallbackUrl;
  }
  
  // 3. Cloud Run: API on same base domain but different service
  // Extract the base domain and replace 'frontend' with 'api'
  const parts = hostname.split('-');
  
  // Try to find 'frontend' in the hostname and replace with 'api'
  if (hostname.includes('frontend-')) {
    const apiHostname = hostname.replace(/frontend[^-]*/g, 'api');
    const apiUrl = `${protocol}//${apiHostname}`;
    console.log(`✅ Cloud Run detected, replacing 'frontend' with 'api':`, apiUrl);
    return apiUrl;
  }
  
  // Fallback: assume API is at /api route
  console.warn('⚠️  Could not determine API URL, using relative path');
  return '/api';
})();

/**
 * Fetch wrapper that automatically adds the API base URL
 * @param {string} endpoint - The endpoint path (e.g., "/auth/login")
 * @param {object} options - Fetch options
 * @returns {Promise<Response>}
 */
export async function apiCall(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  console.log(`[API] ${options.method || 'GET'} ${url}`);
  
  // Ensure credentials are included by default
  if (!options.credentials) {
    options.credentials = 'include';
  }
  
  try {
    const response = await fetch(url, options);
    console.log(`[API] Response: ${response.status} ${response.statusText}`);
    return response;
  } catch (error) {
    console.error(`[API] Error fetching ${url}:`, error);
    throw error;
  }
}

/**
 * Convenience function for GET requests
 */
export function apiGet(endpoint) {
  return apiCall(endpoint, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  });
}

/**
 * Convenience function for POST requests
 */
export function apiPost(endpoint, data = null) {
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  };
  if (data) {
    options.body = JSON.stringify(data);
  }
  return apiCall(endpoint, options);
}

/**
 * Convenience function for PUT requests
 */
export function apiPut(endpoint, data = null) {
  const options = {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' }
  };
  if (data) {
    options.body = JSON.stringify(data);
  }
  return apiCall(endpoint, options);
}

/**
 * Convenience function for DELETE requests
 */
export function apiDelete(endpoint) {
  return apiCall(endpoint, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' }
  });
}
