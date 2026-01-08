/**
 * API utility for centralized API URL management
 */

// Determine API URL - try env var first, then fallback to derived URL
export const API_BASE_URL = (() => {
  // Check environment variable (set at build time or in docker-compose)
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && envUrl.trim() !== '') {
    console.log('✅ Using API URL from environment:', envUrl);
    return envUrl;
  }
  
  // Smart fallback: derive from current hostname
  const hostname = window.location.hostname || 'localhost';
  const protocol = window.location.protocol;
  
  // If running on Cloud Run, API is on same domain but different port
  // If running locally, use localhost:5001
  let fallbackUrl;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    // Local development
    fallbackUrl = `${protocol}//localhost:5001`;
  } else {
    // Cloud Run or other server - API is on same base domain
    // Replace "frontend" with "api" in the hostname
    const apiHostname = hostname.replace('frontend-test', 'api-test').replace('frontend-prod', 'api-prod').replace('frontend', 'api');
    fallbackUrl = `${protocol}//${apiHostname}`;
  }
  
  console.log(`✅ Using fallback API URL: ${fallbackUrl}`);
  console.log(`   (Current hostname: ${hostname})`);
  
  return fallbackUrl;
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
