import { NextRequest, NextResponse } from "next/server";

// Shared-credential review access control, not production authentication (DEC-064).
// Credentials come from Secret Manager at deploy time via PAA_WEB_USERNAME /
// PAA_WEB_PASSWORD environment variables. Never hold a credential in source.
export function proxy(request: NextRequest) {
  const expectedUser = process.env.PAA_WEB_USERNAME;
  const expectedPassword = process.env.PAA_WEB_PASSWORD;

  if (!expectedUser || !expectedPassword) {
    // Fail closed: without configured review credentials, deny rather than let through.
    return new NextResponse("Review access is not configured.", { status: 503 });
  }

  const authHeader = request.headers.get("authorization");
  if (authHeader?.startsWith("Basic ")) {
    const decoded = atob(authHeader.slice("Basic ".length));
    const separatorIndex = decoded.indexOf(":");
    const user = decoded.slice(0, separatorIndex);
    const password = decoded.slice(separatorIndex + 1);
    if (user === expectedUser && password === expectedPassword) {
      return NextResponse.next();
    }
  }

  return new NextResponse("Authentication required.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Player Availability Analysis Review"' },
  });
}

export const config = {
  matcher: "/((?!_next/static|_next/image|favicon.ico).*)",
};
