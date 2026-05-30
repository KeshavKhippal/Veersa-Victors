/**
 * MedAuth Sentinel — Centralized API Configuration
 *
 * Development (npm start):
 *   Uses PUBLIC_API_URL from frontend/.env.development
 *   API_BASE = http://localhost:8000/api
 *
 * Production (Vercel build):
 *   Uses PUBLIC_API_URL from Vercel environment variables
 *   API_BASE = https://your-render-url.onrender.com/api
 */

const API_BASE = (import.meta.env && import.meta.env.PUBLIC_API_URL)
  ? `${import.meta.env.PUBLIC_API_URL}/api`
  : 'http://localhost:8000/api';

export default API_BASE;
