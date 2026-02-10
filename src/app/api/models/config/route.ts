import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL, derived from environment variable or defaulted.
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

export async function GET(request: NextRequest) {
  try {
    // Get query parameters from the request
    const { searchParams } = new URL(request.url);
    const refresh = searchParams.get('refresh');

    // Build target URL with query parameters
    const targetUrl = new URL(`${TARGET_SERVER_BASE_URL}/models/config`);
    if (refresh) {
      targetUrl.searchParams.set('refresh', refresh);
    }

    // Make the actual request to the backend service
    const backendResponse = await fetch(targetUrl.toString(), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    // If the backend service responds with an error
    if (!backendResponse.ok) {
      return NextResponse.json(
        { error: `Backend service responded with status: ${backendResponse.status}` },
        { status: backendResponse.status }
      );
    }

    // Forward the response from the backend
    const modelConfig = await backendResponse.json();
    return NextResponse.json(modelConfig);
  } catch (error) {
    console.error('Error fetching model configurations:', error);    
    return new NextResponse(JSON.stringify({ error: error }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
  }
}

// Handle OPTIONS requests for CORS if needed
export function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
