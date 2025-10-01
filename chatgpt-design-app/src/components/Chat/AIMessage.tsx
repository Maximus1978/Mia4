import React, { useMemo } from 'react';
import MiaIcon from './Icons/MiaIcon';
import sanitizeFinalText from '../../utils/sanitizeFinalText';

interface AIMessageProps { content: string }

const AIMessage: React.FC<AIMessageProps> = ({ content }) => {
    const sanitized = useMemo(() => sanitizeFinalText(content), [content]);
    const scrubbed = sanitized !== content;
    return (
        <div className="ai-message">
            <MiaIcon className="mia-icon" />
            <p
                className="ai-message-text"
                data-scrubbed={scrubbed ? 'true' : undefined}
                data-original={scrubbed ? content : undefined}
            >
                {sanitized}
            </p>
        </div>
    );
};

export default AIMessage;