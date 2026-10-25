import { Toast as BaseToast } from "@base-ui/react/toast";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";

import { cx } from "@/lib/cx";

import styles from "./Toast.module.css";

type ToastInput = {
  title: string;
  description?: string;
  type?: "success" | "error" | "info";
};

type ToastContextValue = {
  showToast: (toast: ToastInput) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

function ToastList() {
  const { toasts } = BaseToast.useToastManager();

  return (
    <BaseToast.Viewport className={styles.viewport}>
      {toasts.map((toast) => (
        <BaseToast.Root
          key={toast.id}
          toast={toast}
          className={cx(
            styles.root,
            toast.type === "error" && styles.error,
            toast.type === "success" && styles.success,
          )}
        >
          <BaseToast.Title className={styles.title}>{toast.title}</BaseToast.Title>
          {toast.description ? (
            <BaseToast.Description className={styles.description}>
              {toast.description}
            </BaseToast.Description>
          ) : null}
        </BaseToast.Root>
      ))}
    </BaseToast.Viewport>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const toastManager = BaseToast.createToastManager();

  const showToast = useCallback(
    (toast: ToastInput) => {
      toastManager.add({
        title: toast.title,
        description: toast.description,
        type: toast.type ?? "info",
      });
    },
    [toastManager],
  );

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <BaseToast.Provider toastManager={toastManager}>
      <ToastContext.Provider value={value}>
        {children}
        <BaseToast.Portal>
          <ToastList />
        </BaseToast.Portal>
      </ToastContext.Provider>
    </BaseToast.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}
