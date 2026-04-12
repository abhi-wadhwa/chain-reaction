import { createContext, useContext, useReducer } from 'react';

const AppContext = createContext();

const initialState = {
  agentTypes: [],
  recentGames: [],
  tournaments: [],
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_AGENT_TYPES':
      return { ...state, agentTypes: action.payload };
    case 'ADD_GAME':
      return { ...state, recentGames: [action.payload, ...state.recentGames].slice(0, 50) };
    case 'ADD_TOURNAMENT':
      return { ...state, tournaments: [action.payload, ...state.tournaments].slice(0, 20) };
    default:
      return state;
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  return useContext(AppContext);
}
