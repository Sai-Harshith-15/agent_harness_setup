export function LoadingSpinner({ text = "Loading..." }: { text?: string }) {
  return (
    <main className="p-8 md:p-12 max-w-7xl mx-auto">
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-accent rounded-full animate-spin" />
        <p className="text-white/40 text-sm">{text}</p>
      </div>
    </main>
  );
}
