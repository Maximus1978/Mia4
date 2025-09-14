import React from 'react';
import './UserMessage.css'; // Assuming you have a CSS file for styling

interface UserMessageProps {
    content: string;
    accentColor?: string;
}

const UserMessage: React.FC<UserMessageProps> = ({ content, accentColor = '#4a90e2' }) => {
    return (
        <div className="user-message" style={{ borderLeft: `4px solid ${accentColor}` }}>
            <p>{content}</p>
        </div>
    );
};

export default UserMessage;