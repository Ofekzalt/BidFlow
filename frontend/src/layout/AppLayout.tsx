import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "@/auth/useAuth";
import { Button } from "@/ui/Button";
import { Stack } from "@/ui/Stack";

import styles from "./AppLayout.module.css";

export function AppLayout() {
  const { user, signOut } = useAuth();

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <NavLink className={styles.brand} to="/auctions">
            BidFlow
          </NavLink>
          <nav className={styles.nav}>
            <NavLink
              className={({ isActive }) =>
                isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
              }
              to="/auctions"
            >
              Auctions
            </NavLink>
            <NavLink
              className={({ isActive }) =>
                isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
              }
              to="/auctions/new"
            >
              Create
            </NavLink>
            <NavLink
              className={({ isActive }) =>
                isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
              }
              to="/account/payment"
            >
              Payment
            </NavLink>
            <NavLink
              className={({ isActive }) =>
                isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
              }
              to="/notifications"
            >
              Notifications
            </NavLink>
          </nav>
          <Stack direction="row" gap="sm" align="center">
            <span className={styles.user}>{user?.email || user?.id}</span>
            <Button variant="secondary" type="button" onClick={signOut}>
              Sign out
            </Button>
          </Stack>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
