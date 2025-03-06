"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useUser } from "@auth0/nextjs-auth0";
import Cookies from "js-cookie";
import {
  ArrowLeft,
  Building,
  Clock,
  Globe,
  MapPin,
  Trash2,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { config } from "../../config";

interface RoleDetails {
  id: string;
  title: string;
  description: string;
  organization_name: string;
  employment_type: string;
  role_mode: string;
  location: {
    city?: string;
    state?: string;
    country?: string;
    remote?: boolean;
  };
  salary: string;
  industry: string;
  level: string;
  requirements: string[];
  preferred_qualifications: string[];
  benefits: string[];
  created_at: string;
  creator_id: string;
}

export default function RoleDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const roleId = params.id as string;
  const { isLoading: isUserLoading } = useUser();
  const [userId, setUserId] = useState<string | undefined>(undefined);
  const [isCreator, setIsCreator] = useState(false);

  const [role, setRole] = useState<RoleDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Get current user ID from cookie
  useEffect(() => {
    const id = Cookies.get("userId");
    if (id) {
      setUserId(id);
    }
  }, []);

  useEffect(() => {
    const fetchRoleDetails = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(
          `${config.apiUrl}/api/roles/role/${roleId}`
        );

        if (!response.ok) {
          throw new Error("Failed to fetch role details");
        }

        const data = await response.json();
        setRole(data);

        // Check if current user is the creator of this role
        if (userId && data.creator_id === userId) {
          setIsCreator(true);
        }

        setError(null);
      } catch (err) {
        console.error("Error fetching role details:", err);
        setError("Failed to load role details. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    };

    if (roleId && userId) {
      fetchRoleDetails();
    }
  }, [roleId, userId]);

  // Handle role deletion
  const handleDeleteRole = async () => {
    if (!confirm("Are you sure you want to delete this role?")) {
      return;
    }

    if (!userId) {
      alert("You must be logged in to delete a role");
      return;
    }

    try {
      setIsDeleting(true);
      const response = await fetch(
        `${config.apiUrl}/api/roles/role/${roleId}?user_id=${userId}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to delete role");
      }

      // Redirect back to dashboard or listings page
      router.push("/");
    } catch (err) {
      console.error("Error deleting role:", err);
      alert(
        err instanceof Error
          ? err.message
          : "Failed to delete role. Please try again later."
      );
    } finally {
      setIsDeleting(false);
    }
  };

  // Format date to readable format
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(date);
  };

  // Helper to format location
  const formatLocation = (location: RoleDetails["location"]) => {
    if (!location) return "Location not specified";

    const parts = [];
    if (location.city) parts.push(location.city);
    if (location.state) parts.push(location.state);
    if (location.country) parts.push(location.country);

    let locationStr = parts.join(", ");
    if (location.remote) {
      locationStr = locationStr
        ? `${locationStr} (Remote available)`
        : "Remote";
    }

    return locationStr || "Location not specified";
  };

  if (isLoading || isUserLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading role details...</p>
        </div>
      </div>
    );
  }

  if (error || !role) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6 bg-white rounded-xl shadow-md">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Error</h2>
          <p className="text-gray-700">{error || "Role not found"}</p>
          <Button
            className="mt-6"
            onClick={() => router.back()}
            variant="outline"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      {/* Header with gradient background */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <Button
            onClick={() => router.back()}
            variant="ghost"
            className="mb-6 text-white hover:bg-white/10"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to listings
          </Button>

          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                {role.title}
              </h1>
              {role.organization_name && (
                <div className="mt-2 flex items-center">
                  <Building className="h-4 w-4 mr-2" />
                  <span>{role.organization_name}</span>
                </div>
              )}
            </div>
            {isCreator ? (
              <Button
                className="mt-4 md:mt-0 bg-red-600 text-white hover:bg-red-700"
                onClick={handleDeleteRole}
                disabled={isDeleting}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {isDeleting ? "Deleting..." : "Delete"}
              </Button>
            ) : (
              <Button className="mt-4 md:mt-0 bg-white text-blue-700 hover:bg-gray-100">
                Apply Now
              </Button>
            )}
          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            {role.employment_type && (
              <div className="flex items-center text-white/90">
                <Clock className="h-4 w-4 mr-2" />
                <span className="capitalize">{role.employment_type}</span>
              </div>
            )}
            {role.role_mode && (
              <div className="flex items-center text-white/90">
                <Globe className="h-4 w-4 mr-2" />
                <span className="capitalize">{role.role_mode}</span>
              </div>
            )}
            {role.location && (
              <div className="flex items-center text-white/90">
                <MapPin className="h-4 w-4 mr-2" />
                <span>{formatLocation(role.location)}</span>
              </div>
            )}
          </div>

          {role.created_at && (
            <div className="mt-6 text-sm text-white/80">
              Posted on {formatDate(role.created_at)}
            </div>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left column - Main job details */}
          <div className="lg:col-span-2 space-y-8">
            {/* Job description */}
            <Card>
              <CardContent className="pt-6">
                <h2 className="text-xl font-semibold mb-4">Job Description</h2>
                <div className="prose max-w-none">
                  <p className="whitespace-pre-line">{role.description}</p>
                </div>
              </CardContent>
            </Card>

            {/* Requirements */}
            {role.requirements && role.requirements.length > 0 && (
              <Card>
                <CardContent className="pt-6">
                  <h2 className="text-xl font-semibold mb-4">Requirements</h2>
                  <ul className="list-disc pl-5 space-y-2">
                    {role.requirements.map((req, index) => (
                      <li key={index} className="text-gray-700">
                        {req}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Preferred qualifications */}
            {role.preferred_qualifications &&
              role.preferred_qualifications.length > 0 && (
                <Card>
                  <CardContent className="pt-6">
                    <h2 className="text-xl font-semibold mb-4">
                      Preferred Qualifications
                    </h2>
                    <ul className="list-disc pl-5 space-y-2">
                      {role.preferred_qualifications.map((qual, index) => (
                        <li key={index} className="text-gray-700">
                          {qual}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
          </div>

          {/* Right column - Additional info */}
          <div className="space-y-6">
            {/* Job details card */}
            <Card>
              <CardContent className="pt-6">
                <h2 className="text-lg font-semibold mb-4">Job Details</h2>
                <div className="space-y-4">
                  {role.salary && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">
                        Salary
                      </h3>
                      <p className="mt-1 text-gray-900">{role.salary}</p>
                    </div>
                  )}

                  {role.industry && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">
                        Industry
                      </h3>
                      <p className="capitalize mt-1 text-gray-900">
                        {role.industry}
                      </p>
                    </div>
                  )}

                  {role.level && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">
                        Experience Level
                      </h3>
                      <p className="capitalize mt-1 text-gray-900">
                        {role.level}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Benefits */}
            {role.benefits && role.benefits.length > 0 && (
              <Card>
                <CardContent className="pt-6">
                  <h2 className="text-lg font-semibold mb-4">Benefits</h2>
                  <div className="flex flex-wrap gap-2">
                    {role.benefits.map((benefit, index) => (
                      <Badge
                        key={index}
                        variant="secondary"
                        className="text-sm"
                      >
                        {benefit}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
