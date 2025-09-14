import React, { createContext, useContext, useState, ReactNode } from 'react';

interface Session {
    id: string;
    title: string;
    createdAt: Date;
}

interface SessionContextType {
    sessions: Session[];
    addSession: (session: Session) => void;
    removeSession: (id: string) => void;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export const SessionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [sessions, setSessions] = useState<Session[]>([]);

    const addSession = (session: Session) => {
        setSessions((prevSessions) => [...prevSessions, session]);
    };

    const removeSession = (id: string) => {
        setSessions((prevSessions) => prevSessions.filter(session => session.id !== id));
    };

    return (
        <SessionContext.Provider value={{ sessions, addSession, removeSession }}>
            {children}
        </SessionContext.Provider>
    );
};

export const useSession = (): SessionContextType => {
    const context = useContext(SessionContext);
    if (context === undefined) {
        throw new Error('useSession must be used within a SessionProvider');
    }
    return context;
};