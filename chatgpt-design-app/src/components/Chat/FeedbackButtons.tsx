import React from 'react';

const FeedbackButtons: React.FC = () => {
    const handleLike = () => {
        // Logic for handling like feedback
    };

    const handleDislike = () => {
        // Logic for handling dislike feedback
    };

    return (
        <div className="feedback-buttons">
            <button onClick={handleLike} className="like-button">
                👍
            </button>
            <button onClick={handleDislike} className="dislike-button">
                👎
            </button>
        </div>
    );
};

export default FeedbackButtons;