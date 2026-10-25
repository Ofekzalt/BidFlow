import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import type { ComponentProps } from "react";

import styles from "./Dialog.module.css";

export const Dialog = {
  Root: BaseDialog.Root,
  Trigger: BaseDialog.Trigger,
  Portal: BaseDialog.Portal,
  Close: BaseDialog.Close,
  Backdrop: (props: ComponentProps<typeof BaseDialog.Backdrop>) => (
    <BaseDialog.Backdrop className={styles.backdrop} {...props} />
  ),
  Popup: (props: ComponentProps<typeof BaseDialog.Popup>) => (
    <BaseDialog.Popup className={styles.popup} {...props} />
  ),
  Title: (props: ComponentProps<typeof BaseDialog.Title>) => (
    <BaseDialog.Title className={styles.title} {...props} />
  ),
  Description: (props: ComponentProps<typeof BaseDialog.Description>) => (
    <BaseDialog.Description className={styles.description} {...props} />
  ),
};
