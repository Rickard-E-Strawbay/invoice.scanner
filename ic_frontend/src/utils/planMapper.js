// Plan mapping utility - fetches and caches plan data from backend
import { API_BASE_URL } from './api';

let plansCache = null;
let cacheTimestamp = null;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export const getPlanMap = async () => {
  // Return cached data if still valid
  if (plansCache && cacheTimestamp && Date.now() - cacheTimestamp < CACHE_DURATION) {
    return plansCache;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/plans`, {
      credentials: "include",
    });

    if (response.ok) {
      const data = await response.json();
      // Create a map from price_plan_key to plan_name
      plansCache = {};
      data.plans.forEach(plan => {
        plansCache[plan.price_plan_key] = plan.plan_name;
      });
      cacheTimestamp = Date.now();
      return plansCache;
    }
  } catch (err) {
    console.error("Error fetching plan map:", err);
  }

  // Return empty map if fetch fails
  return {};
};

export const getPlanName = async (priceplankey) => {
  const planMap = await getPlanMap();
  return planMap[priceplankey] || "Unknown";
};

// Clear cache (useful after plan changes)
export const clearPlanCache = () => {
  plansCache = null;
  cacheTimestamp = null;
};
