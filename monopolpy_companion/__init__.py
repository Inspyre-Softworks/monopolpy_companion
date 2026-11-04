"""MonopolPy Companion's stable, GUI-independent public API.

Importing this package never launches the GUI or starts a game session.
The canonical data models, engine and repository are also available from
`monopolpy_companion.game` for backward compatibility.
"""

from .game import (
    GameEngine,
    MortgageCalculator,
    MortgageQuote,
    PlayerAccount,
    StatisticsService,
    GameplayStatistics,
    FinancialStatistics,
    PlayerReport,
    GameEvent,
    GameRules,
    GameSession,
    MoveResult,
    Player,
    PropertyState,
    SavedSessionInfo,
    SessionRepository,
    Space,
    SpaceType,
    Transaction,
    build_standard_board,
    create_standard_session,
    get_game_logger,
    list_saved_sessions,
    load_session,
    save_session,
)

__all__ = [
    'GameEngine',
    'MortgageCalculator',
    'MortgageQuote',
    'PlayerAccount',
    'StatisticsService',
    'GameplayStatistics',
    'FinancialStatistics',
    'PlayerReport',
    'GameEvent',
    'GameRules',
    'GameSession',
    'MoveResult',
    'Player',
    'PropertyState',
    'SavedSessionInfo',
    'SessionRepository',
    'Space',
    'SpaceType',
    'Transaction',
    'build_standard_board',
    'create_standard_session',
    'get_game_logger',
    'list_saved_sessions',
    'load_session',
    'save_session',
]
