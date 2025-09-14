import React from 'react';

const Diary: React.FC = () => {
    return (
        <div className="diary">
            <h2>Diary</h2>
            <textarea
                placeholder="Write your notes here..."
                className="diary-textarea"
            />
        </div>
    );
};

export default Diary;