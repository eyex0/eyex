import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

const signupSchema = z
  .object({
    fullName: z.string().min(1, "Full name is required"),
    email: z.string().email("Enter a valid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
      .regex(/[0-9]/, "Password must contain at least one number"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type SignupForm = z.infer<typeof signupSchema>;

export default function SignupPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const form = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { fullName: "", email: "", password: "", confirmPassword: "" },
  });

  const onSubmit = async (values: SignupForm) => {
    setSubmitting(true);
    const result = await signUp(values.email, values.password, values.fullName);
    setSubmitting(false);

    if (result.error) {
      toast.error(result.error);
      return;
    }

    if (result.success) {
      if (result.needsEmailVerification) {
        setSubmitted(true);
      } else {
        toast.success("Account created successfully");
        // Auto-navigate to dashboard if no email verification needed
        navigate({ to: "/dashboard" });
      }
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4">
        <div className="w-full max-w-[400px] text-center space-y-6">
          <div className="border border-[#1A1A1C] bg-[#0A0A0C] p-8 space-y-4">
            <div className="mx-auto h-12 w-12 rounded-full border border-[#38BDF8] flex items-center justify-center">
              <svg
                className="h-6 w-6 text-[#38BDF8]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-display font-medium text-[#FAFAFA] tracking-tight">
              Check your email
            </h1>
            <p className="text-sm text-[#A1A1AA] font-light">
              We sent a confirmation link to your email address. Click the link to activate your
              account.
            </p>
          </div>
          <Link
            to="/login"
            className="inline-block text-[10px] text-[#38BDF8] hover:text-[#7dd3fc] uppercase tracking-widest font-medium transition-colors"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4">
      <div className="w-full max-w-[400px] space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-display font-medium text-[#FAFAFA] tracking-tight">
            Create your account
          </h1>
          <p className="text-sm text-[#A1A1AA] font-light">Get started with EyeX Technologies</p>
        </div>

        <div className="border border-[#1A1A1C] bg-[#0A0A0C] p-8">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="fullName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-[#A1A1AA] text-[10px] uppercase tracking-widest font-medium">
                      Full name
                    </FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder="John Doe"
                        className="h-11 bg-[#050505] border-[#1A1A1C] text-[#FAFAFA] placeholder:text-[#A1A1AA] focus-visible:ring-[#38BDF8] focus-visible:border-[#38BDF8]"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-[#A1A1AA] text-[10px] uppercase tracking-widest font-medium">
                      Email
                    </FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="email"
                        placeholder="you@yourcorp.com"
                        className="h-11 bg-[#050505] border-[#1A1A1C] text-[#FAFAFA] placeholder:text-[#A1A1AA] focus-visible:ring-[#38BDF8] focus-visible:border-[#38BDF8]"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-[#A1A1AA] text-[10px] uppercase tracking-widest font-medium">
                      Password
                    </FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="password"
                        placeholder="••••••••"
                        className="h-11 bg-[#050505] border-[#1A1A1C] text-[#FAFAFA] placeholder:text-[#A1A1AA] focus-visible:ring-[#38BDF8] focus-visible:border-[#38BDF8]"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-[#A1A1AA] text-[10px] uppercase tracking-widest font-medium">
                      Confirm password
                    </FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="password"
                        placeholder="••••••••"
                        className="h-11 bg-[#050505] border-[#1A1A1C] text-[#FAFAFA] placeholder:text-[#A1A1AA] focus-visible:ring-[#38BDF8] focus-visible:border-[#38BDF8]"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button
                type="submit"
                disabled={submitting}
                className="w-full h-11 bg-[#FAFAFA] text-[#050505] hover:bg-[#E2E2E2] text-[10px] font-bold uppercase tracking-widest disabled:opacity-50"
              >
                {submitting ? "Creating account..." : "Create account"}
              </Button>
            </form>
          </Form>
        </div>

        <p className="text-center text-sm text-[#A1A1AA]">
          Already have an account?{" "}
          <Link
            to="/login"
            className="text-[#38BDF8] hover:text-[#7dd3fc] font-medium transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
