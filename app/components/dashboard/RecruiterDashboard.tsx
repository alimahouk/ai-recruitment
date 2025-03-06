"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ArrowUpDown, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { User } from "../../../types/user";
import { config } from "../../config";

// Define the RoleListing type based on your schema
interface RoleListing {
  id: string;
  title: string;
  employment_type: string;
  role_mode: string;
  created_at: string;
  is_active: boolean;
  status?: string;
  type: "role"; // Add type field to RoleListing
}

// Add a new interface for RoleProfile
interface RoleProfile {
  id: string;
  title: string;
  employment_type: string;
  role_mode: string;
  created_at: string;
  status: string;
  status_comment?: string;
  type: "profile"; // Add type field to RoleProfile
}

// Create a union type for combined listings
type CombinedListing = RoleListing | RoleProfile;

interface RecruiterDashboardProps {
  user: User;
}

type SortOption = {
  category: "date" | "title" | "applicants";
  order: "asc" | "desc";
};

export default function RecruiterDashboard({
  user,
}: Readonly<RecruiterDashboardProps>) {
  const router = useRouter();
  const [sortOption, setSortOption] = useState<SortOption>({
    category: "date",
    order: "desc", // desc for newest first
  });
  const [combinedListings, setCombinedListings] = useState<CombinedListing[]>(
    []
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchListings = async () => {
      console.log("Fetching listings for user:", user.id);
      try {
        setIsLoading(true);
        const response = await fetch(
          `${config.apiUrl}/api/roles/user-listings/${user.id}`
        );

        if (!response.ok) {
          throw new Error("Failed to fetch listings");
        }

        const data = await response.json();

        // Transform the data to include a type field
        const typedListings = data.listings.map((item: any) => {
          // Determine if it's a role or profile based on properties
          const isProfile =
            "status" in item &&
            (item.status === "pending" || item.status === "failed");

          return {
            ...item,
            type: isProfile ? "profile" : "role",
          } as CombinedListing; // Add type assertion
        });

        setCombinedListings(typedListings || []);
        setError(null);
      } catch (err) {
        console.error("Error fetching listings:", err);
        setError("Failed to load your listings. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchListings();
  }, [user.id]);

  // Sort the listings based on current sort option
  const sortedListings = [...combinedListings].sort((a, b) => {
    if (sortOption.category === "date") {
      const dateA = new Date(a.created_at).getTime();
      const dateB = new Date(b.created_at).getTime();
      return sortOption.order === "asc" ? dateA - dateB : dateB - dateA;
    } else if (sortOption.category === "title") {
      const titleA = a.title || "";
      const titleB = b.title || "";
      return sortOption.order === "asc"
        ? titleA.localeCompare(titleB)
        : titleB.localeCompare(titleA);
    }
    // For applicants, we would need that data - for now just return 0
    return 0;
  });

  const getSortLabel = () => {
    const labels = {
      date: {
        desc: "Newest first",
        asc: "Oldest first",
      },
      title: {
        asc: "A to Z",
        desc: "Z to A",
      },
      applicants: {
        desc: "Most first",
        asc: "Least first",
      },
    };

    return `Sort by: ${sortOption.category} (${
      labels[sortOption.category][sortOption.order]
    })`;
  };

  // Helper function to format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();

    // Calculate difference in milliseconds
    const diffTime = Math.abs(now.getTime() - date.getTime());
    // Convert to days and floor instead of ceiling to avoid rounding up
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Posted today";
    if (diffDays === 1) return "Posted yesterday";
    if (diffDays < 7) return `Posted ${diffDays} days ago`;
    if (diffDays < 30) return `Posted ${Math.floor(diffDays / 7)} weeks ago`;
    return `Posted ${Math.floor(diffDays / 30)} months ago`;
  };

  // Updated helper function to get status display
  const getStatusDisplay = (listing: CombinedListing) => {
    if (listing.type === "profile") {
      if (listing.status === "pending")
        return {
          text: "Processing",
          className: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20",
        };
      if (listing.status === "failed")
        return {
          text: "Failed",
          className: "bg-red-50 text-red-700 ring-1 ring-red-600/20",
        };
    }

    // For role listings
    if (!("is_active" in listing) || !listing.is_active)
      return {
        text: "Inactive",
        className: "bg-gray-50 text-gray-700 ring-1 ring-gray-600/20",
      };

    return {
      text: "Active",
      className: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20",
    };
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6 w-full">
            <h1 className="text-3xl font-bold text-gray-900">
              Recruiter Dashboard
            </h1>
            <div className="flex-grow flex-1"></div>
            <Button onClick={() => router.push("/upload-jd")}>
              <Plus className="mr-2 h-4 w-4" />
              New Listing
            </Button>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              Current Listings
            </h2>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <ArrowUpDown className="mr-2 h-4 w-4" />
                  {getSortLabel()}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>Date Listed</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    <DropdownMenuItem
                      onClick={() =>
                        setSortOption({ category: "date", order: "desc" })
                      }
                      className={
                        sortOption.category === "date" &&
                        sortOption.order === "desc"
                          ? "bg-accent"
                          : ""
                      }
                    >
                      Newest First
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        setSortOption({ category: "date", order: "asc" })
                      }
                      className={
                        sortOption.category === "date" &&
                        sortOption.order === "asc"
                          ? "bg-accent"
                          : ""
                      }
                    >
                      Oldest First
                    </DropdownMenuItem>
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>Title</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    <DropdownMenuItem
                      onClick={() =>
                        setSortOption({ category: "title", order: "asc" })
                      }
                      className={
                        sortOption.category === "title" &&
                        sortOption.order === "asc"
                          ? "bg-accent"
                          : ""
                      }
                    >
                      A to Z
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        setSortOption({ category: "title", order: "desc" })
                      }
                      className={
                        sortOption.category === "title" &&
                        sortOption.order === "desc"
                          ? "bg-accent"
                          : ""
                      }
                    >
                      Z to A
                    </DropdownMenuItem>
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>Applicants</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    <DropdownMenuItem
                      onClick={() =>
                        setSortOption({ category: "applicants", order: "desc" })
                      }
                      className={
                        sortOption.category === "applicants" &&
                        sortOption.order === "desc"
                          ? "bg-accent"
                          : ""
                      }
                    >
                      Most First
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        setSortOption({ category: "applicants", order: "asc" })
                      }
                      className={
                        sortOption.category === "applicants" &&
                        sortOption.order === "asc"
                          ? "bg-accent"
                          : ""
                      }
                    >
                      Least First
                    </DropdownMenuItem>
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {isLoading ? (
            <div className="bg-white shadow-md p-8 rounded-xl border border-gray-100 text-center">
              <p className="text-gray-500">Loading your job listings...</p>
            </div>
          ) : error ? (
            <div className="bg-white shadow-md p-8 rounded-xl border border-gray-100 text-center">
              <p className="text-red-500">{error}</p>
            </div>
          ) : sortedListings.length === 0 ? (
            <div className="bg-white shadow-md p-8 rounded-xl border border-gray-100 text-center">
              <p className="text-gray-500">
                You haven&apos;t posted any roles yet.
              </p>
            </div>
          ) : (
            <div className="bg-white shadow-md overflow-hidden rounded-xl border border-gray-100">
              <div className="divide-y divide-gray-100">
                {sortedListings.map((listing) => {
                  const status = getStatusDisplay(listing);
                  const isProfile = listing.type === "profile";

                  return (
                    <div
                      key={listing.id}
                      className={`group flex items-center justify-between p-6 ${
                        isProfile ? "" : "hover:bg-gray-100 cursor-pointer"
                      } transition-colors duration-200`}
                      onClick={() => {
                        if (!isProfile) {
                          // Navigate to role detail page for role listings
                          router.push(`/role/${listing.id}`);
                        }
                      }}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-6">
                          <div className="min-w-0 flex-1">
                            <h3
                              className={`text-lg font-medium text-gray-900 ${
                                isProfile ? "" : "group-hover:text-blue-600"
                              } truncate transition-colors duration-200`}
                            >
                              {listing.title || "Untitled Position"}
                            </h3>
                            <p className="mt-2 text-sm text-gray-500 flex items-center gap-3">
                              {listing.employment_type && (
                                <>
                                  <span>{listing.employment_type}</span>
                                  <span className="w-1.5 h-1.5 rounded-full bg-gray-300"></span>
                                </>
                              )}
                              {listing.role_mode && (
                                <>
                                  <span>{listing.role_mode}</span>
                                  <span className="w-1.5 h-1.5 rounded-full bg-gray-300"></span>
                                </>
                              )}
                              <span>{formatDate(listing.created_at)}</span>
                            </p>
                            {isProfile && listing.status === "failed" && (
                              <p className="mt-2 text-sm text-red-500">
                                {listing.status_comment || "Processing failed"}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="ml-8 flex items-center gap-6">
                        {!isProfile && (
                          <div className="text-sm font-medium text-gray-900 whitespace-nowrap">
                            0 applicants
                          </div>
                        )}
                        <span
                          className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-medium shadow-sm whitespace-nowrap ${status.className}`}
                        >
                          {status.text}
                        </span>
                        {!isProfile && (
                          <svg
                            className="w-6 h-6 text-gray-400 transform transition-transform duration-200 ease-out group-hover:translate-x-1 group-hover:text-blue-600"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
