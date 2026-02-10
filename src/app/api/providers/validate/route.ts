import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

export async function POST(request: NextRequest) {
  try {
    // Get query parameters from the request
    const { searchParams } = new URL(request.url);
    const provider = searchParams.get('provider');
    const apiKey = searchParams.get('api_key');

    if (!provider) {
      return NextResponse.json(
        { detail: 'Provider parameter is required' },
        { status: 400 }
      );
    }

    // Build target URL with query parameters
    const targetUrl = new URL(`${TARGET_SERVER_BASE_URL}/api/providers/validate`);
    targetUrl.searchParams.set('provider', provider);
    if (apiKey) {
      targetUrl.searchParams.set('api_key', apiKey);
    }

    // Make the actual request to the backend service
    const backendResponse = await fetch(targetUrl.toString(), {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      }
    });

    // If the backend service responds with an error
    if (!backendResponse.ok) {
      const errorData = await backendResponse.json();
      return NextResponse.json(
        errorData,
        { status: backendResponse.status }
      );
    }

    // Forward the response from the backend
    const result = await backendResponse.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error validating provider:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Handle OPTIONS requests for CORS
export function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
