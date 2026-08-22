import { useEffect, useState } from "react";
import { AddProduct } from "./components/AddProduct";
import { CatalogDashboard } from "./components/CatalogDashboard";
import { Header } from "./components/Header";
import { ProductReview } from "./components/ProductReview";
import { ApiError, api, isSeedInProgressDetail } from "./lib/api";
import type { EnrichedProduct, Metrics, ProductPatch, RawProductIn, SortState } from "./types/product";

type View = { name: "dashboard" } | { name: "add" } | { name: "review"; id: number };

function App() {
  const [products, setProducts] = useState<EnrichedProduct[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [view, setView] = useState<View>({ name: "dashboard" });
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = async () => {
    try {
      setMetrics(await api.getMetrics());
    } catch {
      // metrics are supplementary; a failure here shouldn't block the catalog view
    }
  };

  const loadProducts = async () => {
    setLoading(true);
    try {
      setProducts(await api.listProducts());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
    await loadMetrics();
  };

  useEffect(() => {
    loadProducts();
  }, []);

  // If a reseed is already running elsewhere (another tab, or this one
  // after a reload) the backend rejects a second POST with a 409 that
  // carries how many of the total have actually finished. Rather than
  // surface that as a dead-end error, watch it: poll until the count it
  // reported reaches its total, same as if this tab had started it.
  const watchExistingSeed = async (total: number) => {
    const maxWaitMs = 10 * 60 * 1000; // generous cap in case the other run died
    const startedAt = Date.now();
    for (;;) {
      const current = await api.listProducts();
      setProducts(current);
      if (current.length >= total) return;
      if (Date.now() - startedAt > maxWaitMs) {
        throw new Error(`Reseed elsewhere didn't finish after 10 minutes (stuck at ${current.length}/${total}).`);
      }
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
    }
  };

  const seed = async () => {
    setBusy(true);
    setSeeding(true);
    // Reseeding runs a real LLM call per item (~1-1.5s x 211), so the POST
    // itself takes minutes. Poll the product list in the background so the
    // "Enriching… N/211" count actually moves instead of the button just
    // sitting there looking stuck for four minutes.
    const pollId = window.setInterval(() => {
      api.listProducts().then(setProducts).catch(() => {});
    }, 1500);
    try {
      try {
        await api.seedProducts();
      } catch (e) {
        if (e instanceof ApiError && e.status === 409 && isSeedInProgressDetail(e.detail)) {
          await watchExistingSeed(e.detail.total);
        } else {
          throw e;
        }
      }
      await loadProducts();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      window.clearInterval(pollId);
      setSeeding(false);
      setBusy(false);
    }
  };

  const createSingle = async (raw: RawProductIn) => {
    setBusy(true);
    try {
      const created = await api.createProduct(raw);
      await loadProducts();
      setView({ name: "review", id: created.id });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const savePatch = async (id: number, patch: ProductPatch) => {
    setBusy(true);
    try {
      const updated = await api.patchProduct(id, patch);
      setProducts((prev) => prev.map((p) => (p.id === id ? updated : p)));
      await loadMetrics();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const exportCatalog = (format: "csv" | "json", sort: SortState) => {
    window.location.href = api.exportUrl(format, sort);
  };

  const reviewProduct = view.name === "review" ? products.find((p) => p.id === view.id) : undefined;

  return (
    <div className="min-h-screen">
      <Header onHome={() => setView({ name: "dashboard" })} />

      {error && (
        <div
          className="max-w-5xl mx-auto mt-4 px-4 py-2.5 rounded-lg text-sm font-medium"
          style={{ backgroundColor: "var(--danger-soft)", color: "var(--danger)" }}
        >
          {error}
        </div>
      )}

      {view.name === "dashboard" && (
        <CatalogDashboard
          products={products}
          metrics={metrics}
          loading={loading}
          seeding={seeding}
          onOpen={(id) => setView({ name: "review", id })}
          onSeed={seed}
          onAdd={() => setView({ name: "add" })}
          onExport={exportCatalog}
        />
      )}

      {view.name === "add" && (
        <AddProduct onSubmitSingle={createSingle} onCancel={() => setView({ name: "dashboard" })} submitting={busy} />
      )}

      {view.name === "review" &&
        (reviewProduct ? (
          <ProductReview
            product={reviewProduct}
            onBack={() => setView({ name: "dashboard" })}
            onSave={savePatch}
            saving={busy}
          />
        ) : (
          <div className="max-w-5xl mx-auto px-6 py-10 text-sm" style={{ color: "var(--text-muted)" }}>
            Loading product…
          </div>
        ))}
    </div>
  );
}

export default App;
