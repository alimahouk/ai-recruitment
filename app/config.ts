export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  environment: process.env.NODE_ENV || 'development',
  auth0: {
    baseUrl: process.env.AUTH0_BASE_URL || 'http://localhost:3000',
    issuerBaseUrl: process.env.AUTH0_ISSUER_BASE_URL,
    clientId: process.env.AUTH0_CLIENT_ID,
    clientSecret: process.env.AUTH0_CLIENT_SECRET,
  },
}; 