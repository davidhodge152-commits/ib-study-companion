import type { Metadata } from "next";
import { LoginForm } from "@/components/auth/LoginForm";

export const metadata: Metadata = {
  title: "Login",
  description:
    "Sign in to your IB Study Companion account to continue your exam preparation.",
};

export default function LoginPage() {
  return <LoginForm />;
}
