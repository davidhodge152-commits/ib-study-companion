import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";

export default function FlashcardsLoading() {
  return <LoadingSkeleton variant="card" count={6} />;
}
