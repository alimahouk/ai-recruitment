import { Auth0Client } from "@auth0/nextjs-auth0/server";
import { NextResponse } from "next/server";

// Cookie configuration
const COOKIE_CONFIG = {
    httpOnly: false, // False so client-side JS can access it
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    // Set domain to ensure cookie works across subdomains if needed
    // domain: process.env.COOKIE_DOMAIN,
} as const;

const createRedirectResponse = (url: string, userId?: string) => {
    const response = NextResponse.redirect(new URL(url, process.env.APP_BASE_URL));
    
    // Always delete the existing cookie first.
    // Clear the cookie by setting it with an expired date.
    response.cookies.set('userId', '', {
        ...COOKIE_CONFIG,
        maxAge: 0,
    });
    
    // Only set cookie if userId is provided and we're not redirecting to error page
    if (userId && !url.startsWith('/error')) {
        response.cookies.set('userId', userId, COOKIE_CONFIG);
    }
    
    return response;
};

export const auth0 = new Auth0Client({
    async onCallback(error, context, session) {
        // Handle errors early
        if (error) {
            return createRedirectResponse(
                `/error?error=${encodeURIComponent(error.message)}`
            );
        }

        // Validate base URL
        const baseUrl = process.env.APP_BASE_URL?.replace(/\/$/, '');
        if (!baseUrl) {
            return createRedirectResponse(
                `/error?error=${encodeURIComponent('Invalid application configuration')}`
            );
        }

        // Early return if no session or user
        if (!session?.user?.sub) {
            return createRedirectResponse(context.returnTo ?? "/");
        }

        try {
            // Get user identifier
            const identifier = session.user.email ?? session.user.phone_number;
            if (!identifier) {
                return createRedirectResponse(
                    `/error?error=${encodeURIComponent('Email or phone number is required')}`
                );
            }

            const lookupType = session.user.email ? 'email' : 'phone_number';
            const response = await fetch(
                `${baseUrl}/api/users/${encodeURIComponent(identifier)}?lookup_type=${encodeURIComponent(lookupType)}`
            );

            // Handle new user creation
            if (response.status === 404) {
                const newUser = {
                    name: session.user.name ?? null,
                    contact_details: {
                        email: session.user.email ?? null,
                        phone_number: session.user.phone_number ?? null,
                    },
                    profile_picture_url: session.user.picture ?? null,
                };

                const createResponse = await fetch(`${baseUrl}/api/users`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newUser),
                });

                if (!createResponse.ok) {
                    const error = await createResponse.json();
                    return createRedirectResponse(
                        `/error?error=${encodeURIComponent(error.error)}`
                    );
                }

                const newUserData = await createResponse.json();
                // Set cookie for new users during onboarding
                return createRedirectResponse('/upload-cv', newUserData.id);
            }

            // Handle existing user
            const userData = await response.json();
            
            // Redirect to onboarding if needed, maintaining user context with cookie
            if (!userData.is_onboarded) {
                return createRedirectResponse('/upload-cv', userData.id);
            }

            // Check role and redirect accordingly
            if (!userData.role) {
                return createRedirectResponse('/mode-selection', userData.id);
            }

            return createRedirectResponse(
                context.returnTo ?? "/",
                userData.id
            );

        } catch (e) {
            console.error('Error checking/creating user:', e);
            // Redirect to homepage without cookie on error
            return createRedirectResponse("/");
        }
    },
});