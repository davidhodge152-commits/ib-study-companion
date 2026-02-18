"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface PlanInfo {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  planId: string | null; // null = no checkout (free plan)
  highlighted: boolean;
}

const plans: PlanInfo[] = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Get started with the basics",
    features: [
      "5 AI-graded questions per day",
      "3 flashcard decks",
      "Basic study planner",
      "Community access",
      "1 document upload",
    ],
    cta: "Get Started",
    planId: null,
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$9.99",
    period: "/mo",
    description: "For serious IB students",
    features: [
      "Unlimited AI-graded questions",
      "Unlimited flashcard decks",
      "AI study plan generation",
      "AI Tutor with streaming",
      "Insights and gap analysis",
      "Unlimited document uploads",
      "Predicted grades",
      "Priority support",
    ],
    cta: "Upgrade to Pro",
    planId: "scholar",
    highlighted: true,
  },
  {
    name: "Premium",
    price: "$19.99",
    period: "/mo",
    description: "The complete IB toolkit",
    features: [
      "Everything in Pro",
      "Admissions guidance",
      "University matcher",
      "Personal statement feedback",
      "Parent dashboard access",
      "Teacher dashboard access",
      "Advanced analytics",
      "IB Lifecycle tracker",
      "Dedicated support",
    ],
    cta: "Upgrade to Premium",
    planId: "diploma_pass",
    highlighted: false,
  },
];

export default function PricingPage() {
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  async function handleCheckout(planId: string) {
    setLoadingPlan(planId);
    try {
      const data = await api.post<{ url: string }>(
        "/api/billing/checkout",
        { plan_id: planId, interval: "monthly" }
      );
      if (data.url) {
        window.location.href = data.url;
      }
    } catch {
      setLoadingPlan(null);
    }
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Pricing</h1>
        <p className="mt-2 text-muted-foreground">
          Choose the plan that fits your IB journey
        </p>
      </div>

      <div className="mx-auto grid max-w-5xl gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {plans.map((plan) => {
          const isLoading = loadingPlan === plan.planId;

          return (
            <Card
              key={plan.name}
              className={`relative flex flex-col ${
                plan.highlighted
                  ? "border-primary shadow-lg ring-1 ring-primary"
                  : ""
              }`}
            >
              {plan.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-0.5 text-xs font-medium text-primary-foreground">
                  Most Popular
                </div>
              )}
              <CardHeader>
                <CardTitle className="text-xl">{plan.name}</CardTitle>
                <CardDescription>{plan.description}</CardDescription>
                <div className="mt-3">
                  <span className="text-3xl font-bold">{plan.price}</span>
                  <span className="text-sm text-muted-foreground">
                    {plan.period}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="flex-1">
                <ul className="space-y-2.5">
                  {plan.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-sm"
                    >
                      <svg
                        className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter>
                {plan.planId ? (
                  <Button
                    variant={plan.highlighted ? "default" : "outline"}
                    className="w-full"
                    disabled={!!loadingPlan}
                    onClick={() => handleCheckout(plan.planId!)}
                  >
                    {isLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : null}
                    {isLoading ? "Redirecting..." : plan.cta}
                  </Button>
                ) : (
                  <Button asChild variant="outline" className="w-full">
                    <Link href="/register">{plan.cta}</Link>
                  </Button>
                )}
              </CardFooter>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
