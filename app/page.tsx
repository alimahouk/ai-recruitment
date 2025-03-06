import { auth0 } from "@/lib/auth0";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

// Components for different role views
import LandingPage from "./components/LandingPage";
import JobSeekerDashboard from "./components/dashboard/JobSeekerDashboard";
import RecruiterDashboard from "./components/dashboard/RecruiterDashboard";

async function getUserData(userId: string) {
  const response = await fetch(
    `${process.env.BACKEND_URL}/api/users/${userId}`,
    {
      cache: "no-store",
    }
  );

  if (!response.ok) {
    return null;
  }

  return response.json();
}

export default async function HomePage() {
  const session = await auth0.getSession();

  // If no session, show landing page without trying to clear cookies
  if (!session?.user) {
    return <LandingPage />;
  }

  // Get userId from cookie
  const cookieStore = await cookies();
  const userId = cookieStore.get("userId")?.value;

  if (!userId) {
    // Redirect to login if no userId (this shouldn't happen normally)
    redirect("/auth/login");
  }

  // Get user data including role
  const userData = await getUserData(userId);

  if (!userData) {
    // Handle error case
    return <div>Error loading user data</div>;
  }

  // If user is not onboarded, redirect to CV upload
  if (!userData.is_onboarded) {
    redirect("/upload-cv");
  }

  // If user has no role selected, redirect to role selection
  if (!userData.role) {
    redirect("/mode-selection");
  }

  // Render appropriate dashboard based on role
  return userData.role === "recruiter" ? (
    <RecruiterDashboard user={userData} />
  ) : (
    <JobSeekerDashboard user={userData} />
  );
}
