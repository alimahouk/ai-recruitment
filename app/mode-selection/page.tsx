"use client";

import { useUser } from "@auth0/nextjs-auth0";
import Cookies from "js-cookie";
import { useEffect, useState } from "react";

export default function UserRoleSelectionPage() {
  const { user, isLoading } = useUser();
  const [isCheckingStatus, setIsCheckingStatus] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    const checkUserStatus = async () => {
      // If no authenticated user, redirect to home
      if (!isLoading && !user) {
        window.location.href = "/";
        return;
      }

      // Check onboarding status
      const userId = Cookies.get("userId");
      if (userId) {
        try {
          const response = await fetch(
            `http://localhost:8000/api/users/${userId}`
          );
          const userData = await response.json();

          if (!userData.is_onboarded) {
            window.location.href = "/upload-cv";
            return;
          }
        } catch (error) {
          console.error("Error checking user status:", error);
        }
      }
      setIsCheckingStatus(false);
    };

    checkUserStatus();
  }, [user, isLoading]);

  const handleRoleSelection = async (role: "recruiter" | "job_seeker") => {
    setIsUpdating(true);
    const userId = Cookies.get("userId");

    try {
      const response = await fetch(
        `http://localhost:8000/api/users/${userId}/role`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ role }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to update role");
      }

      // Redirect based on role
      window.location.href = role === "recruiter" ? "/upload-jd" : "/";
    } catch (error) {
      console.error("Error updating role:", error);
      // You might want to show an error message to the user here
    } finally {
      setIsUpdating(false);
    }
  };

  if (isLoading || isCheckingStatus) {
    return <div>Loading…</div>;
  }

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
        <h1 className="text-4xl font-bold text-white mb-12">
          What are you looking for?
        </h1>

        <div className="flex gap-6">
          <button
            onClick={() => handleRoleSelection("job_seeker")}
            disabled={isUpdating}
            className="px-8 py-4 bg-white rounded-full text-blue-600 font-semibold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Available Roles
          </button>
          <button
            onClick={() => handleRoleSelection("recruiter")}
            disabled={isUpdating}
            className="px-8 py-4 bg-white rounded-full text-blue-600 font-semibold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Candidates
          </button>
        </div>
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
