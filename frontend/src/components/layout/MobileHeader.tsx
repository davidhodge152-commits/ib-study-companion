"use client";

import { Menu } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { MobileSidebar } from "./MobileSidebar";

export function MobileHeader() {
  return (
    <div className="fixed left-4 top-4 z-50 lg:hidden">
      <Sheet>
        <SheetTrigger asChild>
          <button
            className="flex h-[44px] w-[44px] items-center justify-center rounded-lg bg-slate-900 text-white shadow-lg dark:bg-slate-800"
            aria-label="Open navigation menu"
          >
            <Menu className="h-6 w-6" />
          </button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 bg-slate-900 p-0 text-white border-none">
          <MobileSidebar />
        </SheetContent>
      </Sheet>
    </div>
  );
}
