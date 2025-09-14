import React from 'react';

const SessionsList: React.FC = () => {
    const sessions = [
        { id: 1, name: 'Session 1' },
        { id: 2, name: 'Session 2' },
        { id: 3, name: 'Session 3' },
    ];

    return (
        <div className="sessions-list">
            <h3>Sessions</h3>
            <ul>
                {sessions.map(session => (
                    <li key={session.id} className="session-item">
                        {session.name}
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default SessionsList;