"use client";

import { FileUpload } from "@/components/ui/file-upload";
import { useUser } from "@auth0/nextjs-auth0";
import Cookies from "js-cookie";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { config } from "../config";

export default function UploadJDPage() {
  const { user, isLoading } = useUser();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [userId, setUserId] = useState<string | undefined>(undefined);
  const [jdStatus, setJdStatus] = useState<
    "none" | "pending" | "completed" | "error"
  >("none");

  useEffect(() => {
    // Get userId from cookie
    const id = Cookies.get("userId");
    setUserId(id);

    if (id) {
      // Check user role
      fetch(`${config.apiUrl}/api/users/${id}`)
        .then((response) => response.json())
        .then((user) => {
          if (!user.role) {
            window.location.href = "/mode-selection";
          }
        })
        .catch((error) => {
          console.error("Error checking user status:", error);
        });
    } else {
      console.warn("No userId found in cookies");
    }
  }, []);

  // Show loading state while checking auth
  if (isLoading) return <div>Loading…</div>;

  if (!user) {
    window.location.href = "/auth/login";
    return null;
  }

  const uploadFile = async () => {
    if (!file || !userId) {
      console.error("Missing required file or userId");
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("user_id", userId);

      const response = await fetch(`${config.apiUrl}/api/roles/upload-jd`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Upload error:", errorData);
        throw new Error(errorData.detail?.[0]?.msg || "Upload failed");
      }

      const data = await response.json();
      console.log("Upload successful:", data);

      // Redirect to home page after successful upload
      window.location.href = "/";
    } catch (error) {
      console.error("Error uploading file:", error);
      setJdStatus("error");
    } finally {
      setIsUploading(false);
    }
  };

  // Render different content based on JD status
  const renderContent = () => {
    switch (jdStatus) {
      case "pending":
        return (
          <div className="text-center text-white p-8 bg-white/10 rounded-lg backdrop-blur-sm">
            <h2 className="text-2xl font-bold mb-4">
              Job Description Processing
            </h2>
            <p className="mb-4">
              Your job description is currently being processed. Please check
              back later.
            </p>
            <p className="text-sm text-white/70">
              This usually takes a few minutes.
            </p>
          </div>
        );
      case "error":
        return (
          <div className="text-center text-white p-8 bg-red-500/20 rounded-lg backdrop-blur-sm">
            <h2 className="text-2xl font-bold mb-4">Error</h2>
            <p>
              There was an error checking your job description status. Please
              try again later.
            </p>
          </div>
        );
      default:
        return (
          <FileUpload
            onFileSelect={setFile}
            selectedFile={file}
            uploadButtonLabel="Upload Job Description"
            dragDropText="Drag and drop your job description here, or click to select"
            isUploading={isUploading}
            onUpload={uploadFile}
          />
        );
    }
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
          <Link href="/">
            <Image
              src="/logo.svg"
              alt="AI Recruitment"
              fill
              priority
              className="object-contain filter brightness-200 drop-shadow-[0_0_15px_rgba(255,255,255,0.5)]"
            />
          </Link>
        </div>

        {/* Render content based on JD status */}
        {renderContent()}
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
