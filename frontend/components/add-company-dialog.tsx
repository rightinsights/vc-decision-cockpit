"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { ErrorNotice } from "./notice";

export function AddCompanyDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [website, setWebsite] = useState("");
  const [stage, setStage] = useState("");
  const [geography, setGeography] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const company = await api.createCompany({
        name: name.trim(),
        website: website.trim() || undefined,
        stage: stage || undefined,
        geography: geography.trim() || undefined,
      });
      onOpenChange(false);
      router.push(`/companies/${company.id}?research=1`);  // public research starts automatically in the room
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the company.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>Add a company</DialogTitle>
            <DialogDescription>Name and website are enough to start. Public research runs against the thesis right away; add the deck afterwards for claim-level scoring.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="name">Company name</Label>
              <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="website">Website</Label>
              <Input id="website" value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="stage">Stage</Label>
                <select
                  id="stage"
                  value={stage}
                  onChange={(e) => setStage(e.target.value)}
                  className="h-8 w-full rounded-md border border-input bg-card px-2 text-sm"
                >
                  <option value="">Unknown</option>
                  <option value="pre-seed">Pre-seed</option>
                  <option value="seed">Seed</option>
                  <option value="series A">Series A</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="geography">Geography</Label>
                <Input id="geography" value={geography} onChange={(e) => setGeography(e.target.value)} placeholder="Country" />
              </div>
            </div>
          </div>
          <ErrorNotice message={error} />
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={busy || !name.trim()}>{busy ? "Creating" : "Create company"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
