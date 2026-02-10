import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

export async function POST(request: NextRequest) {
  try {
    // Get query parameters from the request
    const { searchParams } = new URL(request.url);
    const provider = searchParams.get('provider');
    const force = searchParams.get('force');

    if (!provider) {
      return NextResponse.json(
        { detail: 'Provider parameter is required' },
        { status: 400 }
      );
    }

    // Build target URL with query parameters
    const targetUrl = new URL(`${TARGET_SERVER_BASE_URL}/api/providers/refresh`);
    targetUrl.searchParams.set('provider', provider);
    if (force) {
      targetUrl.searchParams.set('force', force);
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
    console.error('Error refreshing provider models:', error);
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
