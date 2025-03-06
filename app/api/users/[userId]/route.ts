import { NextRequest } from "next/server"

export async function GET(
    request: NextRequest,
    context: { params: { userId: string } }
) {
    const { userId } = await context.params
    const { searchParams } = new URL(request.url)
    const lookupType = searchParams.get('lookup_type')
  
    if (!userId) {
        return Response.json({ error: "User ID is required" }, { status: 400 })
    }

    try {
        const response = await fetch(`${process.env.BACKEND_URL}/api/users/${userId}?lookup_type=${encodeURIComponent(lookupType ?? 'id')}`, {
            // Add cache: 'no-store' to prevent caching
            cache: 'no-store'
        })

        if (!response.ok) {
            return Response.json(
                { error: "User not found" }, 
                { status: response.status }
            )
        }

        const data = await response.json()
        return Response.json(data)
    } catch (error) {
        console.error('Error fetching user:', error)
        return Response.json(
            { error: "Failed to fetch user" },
            { status: 500 }
        )
    }
}