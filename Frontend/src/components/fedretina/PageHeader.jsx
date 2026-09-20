/**
 * Shared page heading for signed-in screens.
 * INPUT: title, short description, optional right-hand slot.
 * OUTPUT: an animated heading block used at the top of every inner page.
 */
export function PageHeader({ title, description, action }) {
  return (
    <header className="fr-rise flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {title}
        </h1>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </header>
  );
}
