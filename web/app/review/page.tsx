"use client";

import { Suspense } from "react";
import ReviewInner from "./ReviewInner";

export default function ReviewPage() {
  return (
    <Suspense>
      <ReviewInner />
    </Suspense>
  );
}
