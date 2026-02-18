export default function OfflinePage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 text-center">
      <div>
        <h1 className="text-2xl font-bold">You&apos;re offline</h1>
        <p className="mt-2 text-muted-foreground">
          Check your internet connection and try again.
        </p>
      </div>
    </div>
  );
}
