// API Client
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = {
  baseURL: API_BASE_URL,
  timeout: process.env.NEXT_PUBLIC_API_TIMEOUT || 30000,
};

// Auth
export const AUTH_TOKEN_KEY = "auth_token";
export const REFRESH_TOKEN_KEY = "refresh_token";
