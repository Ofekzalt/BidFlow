import { Navigate, Route, Routes } from "react-router-dom";

import { RequireAuth } from "@/auth/RequireAuth";
import { AppLayout } from "@/layout/AppLayout";
import { AuctionDetailPage } from "@/pages/AuctionDetailPage";
import { AuctionsPage } from "@/pages/AuctionsPage";
import { CreateAuctionPage } from "@/pages/CreateAuctionPage";
import { EditAuctionPage } from "@/pages/EditAuctionPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotificationsPage } from "@/pages/NotificationsPage";
import { PaymentPage } from "@/pages/PaymentPage";
import { RegisterPage } from "@/pages/RegisterPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Navigate to="/auctions" replace />} />
        <Route path="/auctions" element={<AuctionsPage />} />
        <Route path="/auctions/new" element={<CreateAuctionPage />} />
        <Route path="/auctions/:id" element={<AuctionDetailPage />} />
        <Route path="/auctions/:id/edit" element={<EditAuctionPage />} />
        <Route path="/account/payment" element={<PaymentPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/auctions" replace />} />
    </Routes>
  );
}
