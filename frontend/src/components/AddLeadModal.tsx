import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { Lead, PropertyType } from "@/lib/types";
import { Modal } from "@/components/ui/Drawer";
import { Button, Input, Select } from "@/components/ui/Primitives";
import { titleCase } from "@/lib/format";

const PROPERTY_TYPES: PropertyType[] = ["apartment", "villa", "plot", "commercial", "other"];
// Mirrors the backend E.164 validator (schemas.py _E164).
const E164 = /^\+?[1-9]\d{7,14}$/;

interface Form {
  phone_number: string;
  name: string;
  city: string;
  preferred_location: string;
  property_type: "" | PropertyType;
  budget_min: string;
  budget_max: string;
}

const EMPTY: Form = {
  phone_number: "",
  name: "",
  city: "",
  preferred_location: "",
  property_type: "",
  budget_min: "",
  budget_max: "",
};

export function AddLeadModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (lead: Lead) => void;
}) {
  const [form, setForm] = useState<Form>(EMPTY);
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const set = (k: keyof Form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const mut = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = { phone_number: form.phone_number.trim() };
      if (form.name.trim()) body.name = form.name.trim();
      if (form.city.trim()) body.city = form.city.trim();
      if (form.preferred_location.trim()) body.preferred_location = form.preferred_location.trim();
      if (form.property_type) body.property_type = form.property_type;
      if (form.budget_min.trim()) body.budget_min = Number(form.budget_min);
      if (form.budget_max.trim()) body.budget_max = Number(form.budget_max);
      return api.post<Lead>("/leads", body);
    },
    onSuccess: (lead) => onCreated(lead),
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409) {
        setPhoneError("Is number ka lead pehle se maujood hai.");
      } else {
        setFormError(e instanceof Error ? e.message : "Lead create nahi ho paaya.");
      }
    },
  });

  function submit() {
    setPhoneError(null);
    setFormError(null);
    const phone = form.phone_number.trim().replace(/\s/g, "");
    if (!E164.test(phone)) {
      setPhoneError("Valid phone number daalein (E.164, e.g. +9198XXXXXXXX).");
      return;
    }
    if (
      form.budget_min.trim() &&
      form.budget_max.trim() &&
      Number(form.budget_min) > Number(form.budget_max)
    ) {
      setFormError("Budget min, budget max se zyada nahi ho sakta.");
      return;
    }
    mut.mutate();
  }

  return (
    <Modal open onClose={onClose} title="Add Lead" width="max-w-lg">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Input
            label="Phone number *"
            placeholder="+9198XXXXXXXX"
            value={form.phone_number}
            onChange={(e) => { setPhoneError(null); set("phone_number")(e); }}
            aria-invalid={!!phoneError}
          />
          {phoneError && <p className="mt-1 text-xs font-medium text-rose-600">{phoneError}</p>}
        </div>
        <Input label="Name" value={form.name} onChange={set("name")} />
        <Input label="City" value={form.city} onChange={set("city")} />
        <Input label="Preferred location" value={form.preferred_location} onChange={set("preferred_location")} />
        <Select label="Property type" value={form.property_type} onChange={set("property_type")}>
          <option value="">—</option>
          {PROPERTY_TYPES.map((t) => (
            <option key={t} value={t}>{titleCase(t)}</option>
          ))}
        </Select>
        <Input label="Budget min (₹)" type="number" min={0} value={form.budget_min} onChange={set("budget_min")} />
        <Input label="Budget max (₹)" type="number" min={0} value={form.budget_max} onChange={set("budget_max")} />
      </div>

      {formError && <p className="mt-3 text-sm text-rose-600">{formError}</p>}

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={submit} disabled={!form.phone_number.trim() || mut.isPending}>
          {mut.isPending ? "Adding…" : "Add Lead"}
        </Button>
      </div>
    </Modal>
  );
}
