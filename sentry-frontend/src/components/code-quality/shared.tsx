export function PanelSkeleton({ title }: { title: string }) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">{title}</p>
      <div className="h-64 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
    </div>
  );
}

export function Empty({ message }: { message: string }) {
  return (
    <div className="h-64 flex items-center justify-center text-sm text-gray-400">{message}</div>
  );
}