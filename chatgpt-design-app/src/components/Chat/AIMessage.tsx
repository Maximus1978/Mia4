import React from 'react';
import MiaIcon, { MiaIconProps } from './Icons/MiaIcon';

interface AIMessageProps { content: string }

const AIMessage: React.FC<AIMessageProps> = ({ content }) => {
    return (
        <div className="ai-message">
            <MiaIcon className="mia-icon" />
            <p className="ai-message-text">{content}</p>
        </div>
    );
};

export default AIMessage;