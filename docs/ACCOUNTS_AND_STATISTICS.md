# Player accounts and game reports

Every player has a saved account with gameplay and financial history. Choose
**Player account** on the main dashboard to see gameplay, finance and mortgage
tabs.

## PIN-locked accounts

Select **Set / change PIN** to enter a 4-to-8-digit number. PINs are saved
as salted PBKDF2-SHA256 digests, not plaintext. An account's details and
protected game operations require successful verification. **Lock now**
clears the temporary authorization without changing the saved PIN.

PINs are a convenience for players sharing one computer. Session saves are
not encrypted, so they do not provide file-level tamper resistance.

## Gameplay statistics

A player report shows:
- Dice rolled and doubles.
- Total spaces traveled.
- Total properties purchased.
- Turns started and GO crossings.
- Average dice total.

**Roll dice** generates a secure random pair of six-sided dice. The dice
result is recorded for the selected player. **Roll + move** uses the result
immediately. A simulated roll reused for movement is counted once.

Older saved sessions remain readable; events from before statistics were
introduced cannot always be reconstructed.

## Financial statistics

Financial reports include total spending, taxes, other event payments,
purchases and player deals. Rent paid and earned are shown by total, by
opposing player, by property, and as average per turn started.

Reports calculate amounts from persisted ledger entries, not from guessed
cash balances. The transfer dialog lets the banker label a manual payment
as an event, deal or general transfer.

## Mortgages

In the player's **Mortgages** tab, choose Mortgage or Unmortgage, select
multiple eligible properties, and click **Calculate total**. The quote
shows the cost of each deed and the combined amount.

Mortgage proceeds use the printed mortgage value. Payoffs add 10% interest
rounded up to the nearest whole dollar. Before applying a selection, the
engine checks ownership, mortgage state, available funds and applicable
building restrictions.

Calculators only preview; **Apply** makes the validated changes and autosaves.

## Board movement and landing alerts

Dice-based movement highlights the landed-on row. With **Landing alerts**
enabled, the app offers a purchase when a deed is unowned, or displays the
rent due to another owner with an option to pay. This setting is saved in
the game file and can be switched off without disabling highlighting.

The desktop theme uses cream board colors, green, red title panels and
property-group colors. Its app icon is drawn with Qt; system font fallbacks
are used instead of bundling proprietary typefaces.
