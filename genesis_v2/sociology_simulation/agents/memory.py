"""
Advanced memory system for Project Genesis agents.
Provides context-aware memory with sliding windows and semantic retrieval.
"""

import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
from datetime import datetime
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import hashlib


@dataclass
class MemoryContext:
    """Context information for memory retrieval"""
    current_position: Optional[Tuple[int, int]] = None
    current_time: int = 0
    nearby_agents: List[str] = field(default_factory=list)
    current_goals: List[str] = field(default_factory=list)
    emotional_state: Dict[str, float] = field(default_factory=dict)
    urgency: float = 0.5


@dataclass
class MemorySearchResult:
    """Result of memory search"""
    memory: "Memory"
    relevance_score: float
    context_similarity: float
    recency_score: float
    emotional_alignment: float


@dataclass
class Memory:
    """Enhanced memory with semantic features"""
    id: str
    timestamp: int
    type: str  # 'event', 'interaction', 'discovery', 'skill_learned', 'emotion', 'social', 'goal', 'failure', 'success'
    content: Dict[str, Any]
    importance: float  # 0-1 scale
    emotional_impact: float  # -1 to 1 (negative to positive)
    tags: List[str] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)  # agent IDs involved
    position: Optional[Tuple[int, int]] = None
    related_memories: List[str] = field(default_factory=list)
    
    # Semantic features
    embedding: Optional[np.ndarray] = None
    summary: str = ""
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary"""
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'type': self.type,
            'content': self.content,
            'importance': self.importance,
            'emotional_impact': self.emotional_impact,
            'tags': self.tags,
            'participants': self.participants,
            'position': self.position,
            'related_memories': self.related_memories,
            'summary': self.summary,
            'keywords': self.keywords
        }


class SemanticMemorySystem:
    """Advanced memory system with semantic understanding"""
    
    def __init__(self, max_memories: int = 100, embedding_size: int = 100):
        self.max_memories = max_memories
        self.embedding_size = embedding_size
        self.memories: List[Memory] = []
        self.memory_index: Dict[str, Memory] = {}
        self.vectorizer = TfidfVectorizer(max_features=embedding_size, stop_words='english')
        
        # Index for efficient retrieval
        self.type_index: Dict[str, List[Memory]] = {}
        self.participant_index: Dict[str, List[Memory]] = {}
        self.position_index: Dict[Tuple[int, int], List[Memory]] = {}
        self.tag_index: Dict[str, List[Memory]] = {}
        
        # Embedding cache
        self.embedding_cache: Dict[str, np.ndarray] = {}
        
    def add_memory(
        self,
        memory_type: str,
        content: Dict[str, Any],
        importance: float = 0.5,
        emotional_impact: float = 0.0,
        tags: Optional[List[str]] = None,
        participants: Optional[List[str]] = None,
        position: Optional[Tuple[int, int]] = None,
        timestamp: int = 0
    ) -> str:
        """Add a new memory to the system"""
        
        memory_id = self._generate_memory_id(content, timestamp)
        
        # Create summary and keywords
        summary = self._generate_summary(content, memory_type)
        keywords = self._extract_keywords(content, summary)
        
        memory = Memory(
            id=memory_id,
            timestamp=timestamp,
            type=memory_type,
            content=content,
            importance=importance,
            emotional_impact=emotional_impact,
            tags=tags or [],
            participants=participants or [],
            position=position,
            summary=summary,
            keywords=keywords
        )
        
        # Generate embedding
        memory.embedding = self._generate_embedding(memory)
        
        # Add to collections
        self.memories.append(memory)
        self.memory_index[memory_id] = memory
        
        # Update indices
        self._update_indices(memory)
        
        # Manage memory capacity
        self._manage_capacity()
        
        # Find related memories
        self._find_related_memories(memory)
        
        return memory_id
    
    def _generate_memory_id(self, content: Dict[str, Any], timestamp: int) -> str:
        """Generate unique memory ID"""
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.md5(f"{content_str}_{timestamp}".encode()).hexdigest()[:12]
    
    def _generate_summary(self, content: Dict[str, Any], memory_type: str) -> str:
        """Generate human-readable summary"""
        if memory_type == "event":
            return f"{content.get('action', 'something')} happened at {content.get('location', 'unknown')}"
        elif memory_type == "interaction":
            return f"Interaction with {content.get('agent', 'someone')}: {content.get('outcome', 'unknown')}"
        elif memory_type == "discovery":
            return f"Discovered {content.get('item', 'something')} at {content.get('location', 'unknown')}"
        elif memory_type == "emotion":
            return f"Felt {content.get('emotion', 'emotion')} due to {content.get('cause', 'unknown')}"
        else:
            return f"{memory_type}: {str(content)[:50]}..."
    
    def _extract_keywords(self, content: Dict[str, Any], summary: str) -> List[str]:
        """Extract keywords from content"""
        text = summary + " " + json.dumps(content)
        
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 3 and word.isalpha()]
        
        # Remove duplicates and limit
        return list(set(keywords))[:10]
    
    def _generate_embedding(self, memory: Memory) -> np.ndarray:
        """Generate semantic embedding for memory"""
        text = f"{memory.summary} {' '.join(memory.keywords)} {json.dumps(memory.content)}"
        
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        try:
            # Simple TF-IDF embedding
            if len(self.memories) > 0:
                texts = [f"{m.summary} {' '.join(m.keywords)}" for m in self.memories] + [text]
                tfidf_matrix = self.vectorizer.fit_transform(texts)
                embedding = tfidf_matrix[-1].toarray()[0]
            else:
                embedding = np.random.rand(self.embedding_size)
            
            self.embedding_cache[text] = embedding
            return embedding
            
        except Exception:
            return np.random.rand(self.embedding_size)
    
    def _update_indices(self, memory: Memory):
        """Update search indices"""
        # Type index
        if memory.type not in self.type_index:
            self.type_index[memory.type] = []
        self.type_index[memory.type].append(memory)
        
        # Participant index
        for participant in memory.participants:
            if participant not in self.participant_index:
                self.participant_index[participant] = []
            self.participant_index[participant].append(memory)
        
        # Position index
        if memory.position:
            if memory.position not in self.position_index:
                self.position_index[memory.position] = []
            self.position_index[memory.position].append(memory)
        
        # Tag index
        for tag in memory.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(memory)
    
    def _manage_capacity(self):
        """Manage memory capacity using importance-based forgetting"""
        if len(self.memories) <= self.max_memories:
            return
        
        # Calculate forgetting scores
        current_time = max([m.timestamp for m in self.memories]) if self.memories else 0
        
        scores = []
        for memory in self.memories:
            # Recency score (decay over time)
            time_decay = 0.95 ** (current_time - memory.timestamp)
            
            # Importance score
            importance_score = memory.importance
            
            # Emotional salience
            emotional_score = abs(memory.emotional_impact)
            
            # Combined score
            total_score = (importance_score * 0.4 + 
                         emotional_score * 0.3 + 
                         time_decay * 0.3)
            
            scores.append((memory, total_score))
        
        # Keep top memories
        scores.sort(key=lambda x: x[1], reverse=True)
        memories_to_keep = [m[0] for m in scores[:self.max_memories]]
        
        # Update collections
        self.memories = memories_to_keep
        self.memory_index = {m.id: m for m in memories_to_keep}
        
        # Rebuild indices
        self._rebuild_indices()
    
    def _rebuild_indices(self):
        """Rebuild all indices"""
        self.type_index = {}
        self.participant_index = {}
        self.position_index = {}
        self.tag_index = {}
        
        for memory in self.memories:
            self._update_indices(memory)
    
    def _find_related_memories(self, new_memory: Memory):
        """Find and link related memories"""
        related = []
        
        for existing_memory in self.memories:
            if existing_memory.id == new_memory.id:
                continue
            
            # Check for related participants
            common_participants = set(new_memory.participants) & set(existing_memory.participants)
            if common_participants:
                related.append(existing_memory.id)
            
            # Check for similar locations
            if (new_memory.position and existing_memory.position and 
                abs(new_memory.position[0] - existing_memory.position[0]) <= 3 and
                abs(new_memory.position[1] - existing_memory.position[1]) <= 3):
                related.append(existing_memory.id)
            
            # Check for similar content
            if new_memory.type == existing_memory.type:
                similarity = self._calculate_similarity(new_memory, existing_memory)
                if similarity > 0.7:
                    related.append(existing_memory.id)
        
        new_memory.related_memories = related[:5]  # Limit to 5 related memories
    
    def _calculate_similarity(self, memory1: Memory, memory2: Memory) -> float:
        """Calculate semantic similarity between memories"""
        if memory1.embedding is None or memory2.embedding is None:
            return 0.0
        
        try:
            similarity = cosine_similarity(
                [memory1.embedding], 
                [memory2.embedding]
            )[0][0]
            return max(0.0, min(1.0, similarity))
        except Exception:
            return 0.0
    
    def search_memories(
        self,
        query: str = "",
        memory_type: Optional[str] = None,
        context: Optional[MemoryContext] = None,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[MemorySearchResult]:
        """Search memories with context-aware ranking"""
        
        candidates = self.memories
        
        # Filter by type
        if memory_type:
            candidates = [m for m in candidates if m.type == memory_type]
        
        # Filter by importance
        candidates = [m for m in candidates if m.importance >= min_importance]
        
        # Calculate scores
        results = []
        for memory in candidates:
            scores = self._calculate_search_scores(memory, query, context)
            results.append(MemorySearchResult(
                memory=memory,
                **scores
            ))
        
        # Sort by combined score
        results.sort(key=lambda r: 
            r.relevance_score * 0.4 + 
            r.context_similarity * 0.3 + 
            r.recency_score * 0.2 + 
            r.emotional_alignment * 0.1,
            reverse=True
        )
        
        return results[:limit]
    
    def _calculate_search_scores(
        self, 
        memory: Memory, 
        query: str, 
        context: Optional[MemoryContext]
    ) -> Dict[str, float]:
        """Calculate various search scores for a memory"""
        
        # Text relevance
        if query and memory.embedding is not None:
            query_embedding = self._generate_embedding_for_text(query)
            relevance = cosine_similarity([memory.embedding], [query_embedding])[0][0]
        else:
            relevance = 0.5
        
        # Context similarity
        context_sim = 0.5
        if context:
            # Position similarity
            if memory.position and context.current_position:
                distance = abs(memory.position[0] - context.current_position[0]) + \
                          abs(memory.position[1] - context.current_position[1])
                position_sim = max(0, 1 - distance / 10)
            else:
                position_sim = 0.5
            
            # Participant similarity
            if context.nearby_agents and memory.participants:
                common = set(context.nearby_agents) & set(memory.participants)
                participant_sim = len(common) / max(len(context.nearby_agents), 1)
            else:
                participant_sim = 0.5
            
            context_sim = (position_sim + participant_sim) / 2
        
        # Recency score
        current_time = max([m.timestamp for m in self.memories]) if self.memories else 0
        recency = 0.95 ** (max(0, current_time - memory.timestamp))
        
        # Emotional alignment
        emotional = abs(memory.emotional_impact) * 0.5 + 0.5
        
        return {
            'relevance_score': max(0.0, min(1.0, relevance)),
            'context_similarity': context_sim,
            'recency_score': recency,
            'emotional_alignment': emotional
        }
    
    def _generate_embedding_for_text(self, text: str) -> np.ndarray:
        """Generate embedding for search query"""
        try:
            # Use existing vectorizer if available
            if hasattr(self.vectorizer, 'vocabulary_') and self.vectorizer.vocabulary_:
                embedding = self.vectorizer.transform([text]).toarray()[0]
            else:
                embedding = self._generate_embedding(Memory(
                    id="query",
                    timestamp=0,
                    type="query",
                    content={"text": text},
                    importance=1.0,
                    emotional_impact=0.0,
                    summary=text
                ))
            return embedding
        except Exception:
            return np.random.rand(self.embedding_size)
    
    def get_memories_by_type(self, memory_type: str, limit: int = 10) -> List[Memory]:
        """Get memories by type"""
        return self.type_index.get(memory_type, [])[-limit:]
    
    def get_memories_by_participant(self, participant_id: str, limit: int = 10) -> List[Memory]:
        """Get memories involving specific participant"""
        return self.participant_index.get(participant_id, [])[-limit:]
    
    def get_memories_by_location(self, position: Tuple[int, int], radius: int = 3, limit: int = 10) -> List[Memory]:
        """Get memories from nearby locations"""
        memories = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nearby_pos = (position[0] + dx, position[1] + dy)
                memories.extend(self.position_index.get(nearby_pos, []))
        
        # Sort by distance and recency
        memories.sort(key=lambda m: 
            abs(m.position[0] - position[0]) + abs(m.position[1] - position[1]) if m.position else 100,
            reverse=False
        )
        
        return memories[:limit]
    
    def get_recent_memories(self, memory_type: Optional[str] = None, limit: int = 10) -> List[Memory]:
        """Get recent memories"""
        memories = self.memories
        if memory_type:
            memories = [m for m in memories if m.type == memory_type]
        
        return memories[-limit:] if memories else []
    
    def get_context_summary(self, context: MemoryContext, max_length: int = 1000) -> str:
        """Generate context summary for LLM prompts"""
        
        # Get relevant memories
        relevant_memories = self.search_memories(
            context=context,
            limit=10
        )
        
        if not relevant_memories:
            return "No relevant memories found."
        
        # Build context string
        context_parts = []
        
        for result in relevant_memories:
            memory = result.memory
            
            # Format based on memory type
            if memory.type == "interaction":
                part = f"- Interaction with {memory.participants}: {memory.summary} (importance: {memory.importance:.2f})"
            elif memory.type == "discovery":
                part = f"- Discovered: {memory.summary} at {memory.position}"
            elif memory.type == "event":
                part = f"- Event: {memory.summary} (emotional: {memory.emotional_impact:.2f})"
            else:
                part = f"- {memory.type}: {memory.summary}"
            
            context_parts.append(part)
        
        # Add recent highlights
        recent_highlights = self.get_recent_memories(limit=3)
        if recent_highlights:
            context_parts.append("\nRecent highlights:")
            for memory in recent_highlights:
                context_parts.append(f"- {memory.summary}")
        
        return "\n".join(context_parts)[:max_length]
    
    def get_emotional_memory_summary(self) -> Dict[str, float]:
        """Get summary of emotional experiences"""
        emotional_summary = {}
        
        for memory in self.memories:
            if memory.emotional_impact != 0:
                emotion_type = "positive" if memory.emotional_impact > 0 else "negative"
                if emotion_type not in emotional_summary:
                    emotional_summary[emotion_type] = 0
                emotional_summary[emotion_type] += abs(memory.emotional_impact)
        
        return emotional_summary
    
    def forget_memories(self, threshold: float = 0.1):
        """Forget low-importance memories"""
        memories_to_keep = [m for m in self.memories if m.importance >= threshold]
        
        if len(memories_to_keep) < len(self.memories):
            self.memories = memories_to_keep
            self._rebuild_indices()
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get statistics about memory system"""
        return {
            "total_memories": len(self.memories),
            "memory_types": {
                memory_type: len(memories) 
                for memory_type, memories in self.type_index.items()
            },
            "average_importance": np.mean([m.importance for m in self.memories]) if self.memories else 0,
            "emotional_range": {
                "min": min([m.emotional_impact for m in self.memories]) if self.memories else 0,
                "max": max([m.emotional_impact for m in self.memories]) if self.memories else 0,
                "avg": np.mean([m.emotional_impact for m in self.memories]) if self.memories else 0
            },
            "unique_participants": len(self.participant_index),
            "unique_locations": len(self.position_index),
            "unique_tags": len(self.tag_index)
        }