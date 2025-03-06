export interface User {
  id: string;
  name: string | null;
  role: "recruiter" | "job_seeker";
  is_onboarded: boolean;
  contact_details: {
    email: string | null;
    phone_number: string | null;
  };
  profile_picture_url: string | null;
  // Add other user fields as needed
}
