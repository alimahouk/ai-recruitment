import { NextRequest } from "next/server"

export async function POST(request: NextRequest) {
    const body = await request.json()
    
    const response = await fetch(`${process.env.BACKEND_URL}/api/users`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
    })

    const data = await response.json()
    return Response.json(data, { status: response.status })
}