// Author: Bradley R. Kinnard — accept/reject with star rating
import { useState } from 'react'

interface RatingPanelProps {
  onAccept: (rating: number) => void
  onReject: (rating: number) => void
}

export default function RatingPanel({ onAccept, onReject }: RatingPanelProps) {
  const [rating, setRating] = useState(3)
  const [hoverRating, setHoverRating] = useState(0)

  const displayRating = hoverRating || rating

  return (
    <div className="rating-panel">
      <div className="star-rating">
        {[1, 2, 3, 4, 5].map(star => (
          <button
            key={star}
            className={`star ${star <= displayRating ? 'filled' : ''}`}
            onMouseEnter={() => setHoverRating(star)}
            onMouseLeave={() => setHoverRating(0)}
            onClick={() => setRating(star)}
          >
            ★
          </button>
        ))}
        <span className="rating-label">{rating}/5</span>
      </div>

      <div className="feedback-buttons">
        <button
          className="accept-btn"
          onClick={() => onAccept(rating)}
        >
          ✓ Accept
        </button>
        <button
          className="reject-btn"
          onClick={() => onReject(rating)}
        >
          ✕ Reject
        </button>
      </div>
    </div>
  )
}
