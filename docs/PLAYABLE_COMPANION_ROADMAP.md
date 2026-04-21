# MonopolPy Companion Roadmap

## Project Summary
MonopolPy Companion is best treated as a Monopoly session companion for a physical board game, not a full digital board game client. The app should manage players, money, property ownership, session state, saves, and guided rule workflows so a real Monopoly game can be played with the app as banker and record keeper.

## Current Baseline
- The app now has a bootable GUI shell.
- A standard Monopoly board model exists in code.
- Sessions can be created, saved, loaded, and summarized.
- Players, transactions, ownership, and turn order have foundational models.

## MVP
Goal: a group can sit down with a physical Monopoly board and use the app as banker and ledger.

1. Session setup
- Start a new session with house rules and player names.
- Edit and remove players before play begins.
- Persist all setup data to a save file.

2. Banker tools
- Record bank-to-player and player-to-bank cash transfers.
- Record player-to-player payments.
- Show current balances, bankrupt state, and transaction history.

3. Property ownership
- Buy unowned properties from the bank.
- Track current ownership for properties, railroads, and utilities.
- Display owned assets per player.

4. Turn tracking
- Advance current player.
- Track board position.
- Record pass-GO salary.

5. Save/load stability
- Save at any time.
- Autosave after meaningful actions.
- Restore a session exactly as it was.

## Playable Companion
Goal: the app can support a full standard Monopoly game without paper bookkeeping.

1. Board resolution
- Move players by dice roll.
- Resolve landing outcomes for property, railroad, utility, tax, cards, jail, and go-to-jail.

2. Rent engine
- Calculate rent for standard properties.
- Calculate railroad rent by count owned.
- Calculate utility rent from dice rules.
- Block rent collection when a property is mortgaged.

3. Mortgage workflow
- Mortgage and unmortgage properties.
- Enforce monopoly and building constraints around mortgaging.

4. Building workflow
- Buy and sell houses and hotels.
- Enforce even-building rules across a color group.
- Track remaining house and hotel state in-session.

5. Jail flow
- Send players to jail.
- Track jail turns.
- Handle paying out, doubles, and get-out-of-jail cards.

6. Chance and Community Chest
- Implement the standard card decks.
- Support draw, apply, discard, and reshuffle behavior.

7. Auction workflow
- Start and run an auction for declined properties.
- Assign winner and update money and ownership.

## Nice-to-Have Features
1. Trade builder for cash, deeds, cards, and optional loans.
2. Undo last action with transaction rollback safeguards.
3. Rule presets for common house rules.
4. Session analytics: richest player, monopoly counts, rent exposure.
5. Exportable end-of-game summary.
6. Better visual board/dashboard UI.

## Recommended Build Order
1. Finish banker actions and asset ownership UI.
2. Add board position and dice-driven movement.
3. Add rent resolution.
4. Add mortgages and buildings.
5. Add jail and cards.
6. Add auctions.
7. Add trade mediation and undo support.

## Definition Of Done For “Playable Companion”
- A new session can be created and saved.
- Any standard Monopoly turn can be recorded in the app.
- The app can accurately track money, ownership, rent, jail state, mortgages, and buildings.
- The session can be resumed later without losing game state.
