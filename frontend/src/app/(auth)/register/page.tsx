import type { Metadata } from "next";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata: Metadata = {
  title: "Register",
  description:
    "Create a free IB Study Companion account. Get AI-powered exam prep, flashcards, and grade predictions.",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
