"use client";

import Image from "next/image";

export default function LandingPage() {
  const handleLogin = async () => {
    window.location.href = "/auth/login";
  };

  return (
    <div className="min-h-screen w-full flex flex-col bg-gradient-to-br from-blue-900 via-blue-600 to-blue-400 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 w-full h-full opacity-10">
        <div className="absolute w-96 h-96 -top-48 -left-48 bg-blue-200 rounded-full mix-blend-soft-light filter blur-xl animate-pulse"></div>
        <div
          className="absolute w-96 h-96 -bottom-48 -right-48 bg-blue-200 rounded-full mix-blend-soft-light filter blur-xl animate-pulse"
          style={{ animationDelay: "1s" }}
        ></div>
      </div>

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.1)_1px,transparent_1px)] bg-[size:40px_40px]"></div>

      {/* Main content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center">
        {/* Logo container */}
        <div className="mb-8 relative w-96 h-40">
          <Image
            src="/logo.svg"
            alt="AI Recruitment"
            fill
            priority
            className="object-contain filter brightness-200 drop-shadow-[0_0_15px_rgba(255,255,255,0.5)]"
          />
        </div>

        {/* Login button */}
        <button
          onClick={handleLogin}
          className="px-8 py-4 bg-white rounded-full text-blue-600 font-semibold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
        >
          Log In
        </button>
      </div>

      {/* Footer */}
      <footer className="backdrop-blur-sm bg-white/10 relative z-10 w-full py-4 px-6">
        <div className="max-w-6xl mx-auto flex justify-center items-center text-white/70 text-sm">
          <span>© 2025 Ali Mahouk</span>
          <span className="mx-2">•</span>
          <a href="/privacy" className="hover:text-white">
            Privacy Policy
          </a>
          <span className="mx-2">•</span>
          <a href="/terms" className="hover:text-white">
            Terms of Service
          </a>
          <span className="mx-2">•</span>
          <a href="/contact" className="hover:text-white">
            Contact
          </a>
        </div>
      </footer>
    </div>
  );
}
