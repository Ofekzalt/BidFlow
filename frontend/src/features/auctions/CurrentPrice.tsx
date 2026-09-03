import { formatMoney } from "@/format/money";
import { Text } from "@/ui/Text";

type CurrentPriceProps = {
  cents: number;
};

export function CurrentPrice({ cents }: CurrentPriceProps) {
  return (
    <Text variant="data" className="current-price">
      {formatMoney(cents)}
    </Text>
  );
}
