"""
CRM Service using SQLite and Google Sheets (optional)
Handles contact management and interaction logging
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import json
import gspread
from google.oauth2.service_account import Credentials
from app.config import settings

class CRMService:
    """CRM Service for contact and interaction management"""
    
    def __init__(self, use_google_sheets: bool = False, sheets_creds_path: Optional[str] = None):
        """
        Initialize CRM service
        
        Args:
            use_google_sheets: Whether to use Google Sheets as CRM backend
            sheets_creds_path: Path to Google service account credentials
        """
        self.use_google_sheets = use_google_sheets
        self.sheets_creds_path = sheets_creds_path
        
        if use_google_sheets and sheets_creds_path:
            self._init_google_sheets()
        else:
            self._init_sqlite()
    
    def _init_sqlite(self):
        """Initialize SQLite CRM database"""
        self.conn = sqlite3.connect('crm.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        
        cursor = self.conn.cursor()
        
        # Create contacts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                company TEXT,
                title TEXT,
                notes TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP,
                interaction_count INTEGER DEFAULT 0
            )
        """)
        
        # Create interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                interaction_type TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_seconds INTEGER,
                summary TEXT,
                sentiment TEXT,
                action_items TEXT,
                recording_url TEXT,
                metadata TEXT,
                FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contact_email ON contacts(email)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_interaction_contact ON interactions(contact_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_interaction_date ON interactions(date)
        """)
        
        self.conn.commit()
        print("✅ SQLite CRM database initialized")
    
    def _init_google_sheets(self):
        """Initialize Google Sheets CRM"""
        try:
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(
                self.sheets_creds_path,
                scopes=scope
            )
            
            self.gc = gspread.authorize(creds)
            
            # Open or create spreadsheet
            try:
                self.spreadsheet = self.gc.open('Call Tracker CRM')
            except gspread.SpreadsheetNotFound:
                self.spreadsheet = self.gc.create('Call Tracker CRM')
                # Share with your email
                # self.spreadsheet.share('your-email@example.com', perm_type='user', role='writer')
            
            # Get or create worksheets
            try:
                self.contacts_sheet = self.spreadsheet.worksheet('Contacts')
            except gspread.WorksheetNotFound:
                self.contacts_sheet = self.spreadsheet.add_worksheet('Contacts', 1000, 10)
                self.contacts_sheet.append_row([
                    'ID', 'Name', 'Email', 'Phone', 'Company', 'Title', 
                    'Last Interaction', 'Interaction Count', 'Tags', 'Notes'
                ])
            
            try:
                self.interactions_sheet = self.spreadsheet.worksheet('Interactions')
            except gspread.WorksheetNotFound:
                self.interactions_sheet = self.spreadsheet.add_worksheet('Interactions', 1000, 10)
                self.interactions_sheet.append_row([
                    'ID', 'Contact Name', 'Contact Email', 'Date', 'Type',
                    'Duration', 'Summary', 'Sentiment', 'Action Items'
                ])
            
            print("✅ Google Sheets CRM initialized")
        
        except Exception as e:
            print(f"❌ Failed to initialize Google Sheets: {str(e)}")
            print("Falling back to SQLite")
            self.use_google_sheets = False
            self._init_sqlite()
    
    async def create_or_update_contact(self, contact_data: Dict) -> Optional[int]:
        """
        Create a new contact or update existing one
        
        Args:
            contact_data: Dict with contact information
            
        Returns:
            Contact ID
        """
        
        if self.use_google_sheets:
            return await self._create_contact_sheets(contact_data)
        else:
            return await self._create_contact_sqlite(contact_data)
    
    async def _create_contact_sqlite(self, contact_data: Dict) -> Optional[int]:
        """Create or update contact in SQLite"""
        cursor = self.conn.cursor()
        
        email = contact_data.get('email')
        
        # Check if contact exists
        if email:
            cursor.execute("SELECT id FROM contacts WHERE email = ?", (email,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing contact
                contact_id = existing[0]
                
                update_fields = []
                update_values = []
                
                for field in ['name', 'phone', 'company', 'title', 'notes']:
                    if field in contact_data:
                        update_fields.append(f"{field} = ?")
                        update_values.append(contact_data[field])
                
                # Handle tags separately (convert to JSON)
                if 'tags' in contact_data:
                    update_fields.append("tags = ?")
                    update_values.append(json.dumps(contact_data['tags']))
                
                if update_fields:
                    update_values.append(contact_id)
                    cursor.execute(
                        f"UPDATE contacts SET {', '.join(update_fields)} WHERE id = ?",
                        update_values
                    )
                    self.conn.commit()
                
                return contact_id
        
        # Create new contact
        # Convert tags list to JSON string
        tags_json = json.dumps(contact_data.get('tags', []))
        
        cursor.execute("""
            INSERT INTO contacts (name, email, phone, company, title, notes, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            contact_data.get('name', 'Unknown'),
            contact_data.get('email'),
            contact_data.get('phone'),
            contact_data.get('company'),
            contact_data.get('title'),
            contact_data.get('notes'),
            tags_json  # Changed: Now it's a JSON string
        ))
        
        self.conn.commit()
        return cursor.lastrowid
        
    async def _create_contact_sheets(self, contact_data: Dict) -> Optional[int]:
        """Create or update contact in Google Sheets"""
        try:
            email = contact_data.get('email')
            
            # Find existing contact
            existing_row = None
            if email:
                cell = self.contacts_sheet.find(email)
                if cell:
                    existing_row = cell.row
            
            if existing_row:
                # Update existing
                # Implementation depends on what fields to update
                pass
            else:
                # Add new contact
                row_data = [
                    '',  # ID (auto-generated by sheets)
                    contact_data.get('name', 'Unknown'),
                    contact_data.get('email', ''),
                    contact_data.get('phone', ''),
                    contact_data.get('company', ''),
                    contact_data.get('title', ''),
                    '',  # Last interaction
                    0,   # Interaction count
                    json.dumps(contact_data.get('tags', [])),
                    contact_data.get('notes', '')
                ]
                self.contacts_sheet.append_row(row_data)
            
            return 1  # Return dummy ID for sheets
        
        except Exception as e:
            print(f"❌ Error creating contact in sheets: {str(e)}")
            return None
    
    async def log_interaction(self, interaction_data: Dict) -> bool:
        """
        Log a call/meeting interaction
        
        Args:
            interaction_data: Dict with interaction details
            
        Returns:
            True if successful
        """
        
        if self.use_google_sheets:
            return await self._log_interaction_sheets(interaction_data)
        else:
            return await self._log_interaction_sqlite(interaction_data)
    
    async def _log_interaction_sqlite(self, interaction_data: Dict) -> bool:
        """Log interaction in SQLite"""
        try:
            cursor = self.conn.cursor()
            
            # Get or create contact
            contact_id = await self._get_or_create_contact_by_email(
                interaction_data.get('contact_email'),
                interaction_data.get('contact_name', 'Unknown')
            )
            
            # Insert interaction
            cursor.execute("""
                INSERT INTO interactions (
                    contact_id, interaction_type, date, duration_seconds,
                    summary, sentiment, action_items, recording_url, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact_id,
                interaction_data.get('type', 'call'),
                interaction_data.get('date', datetime.utcnow()),
                interaction_data.get('duration_seconds', 0),
                interaction_data.get('summary'),
                interaction_data.get('sentiment'),
                json.dumps(interaction_data.get('action_items', [])),
                interaction_data.get('recording_url'),
                json.dumps(interaction_data.get('metadata', {}))
            ))
            
            # Update contact last interaction
            cursor.execute("""
                UPDATE contacts 
                SET last_interaction = ?,
                    interaction_count = interaction_count + 1
                WHERE id = ?
            """, (datetime.utcnow(), contact_id))
            
            self.conn.commit()
            print(f"✅ Interaction logged for contact {contact_id}")
            return True
        
        except Exception as e:
            print(f"❌ Error logging interaction: {str(e)}")
            return False
    
    async def _log_interaction_sheets(self, interaction_data: Dict) -> bool:
        """Log interaction in Google Sheets"""
        try:
            row_data = [
                '',  # ID
                interaction_data.get('contact_name', 'Unknown'),
                interaction_data.get('contact_email', ''),
                interaction_data.get('date', datetime.utcnow()).isoformat(),
                interaction_data.get('type', 'call'),
                interaction_data.get('duration_seconds', 0),
                interaction_data.get('summary', ''),
                interaction_data.get('sentiment', ''),
                json.dumps(interaction_data.get('action_items', []))
            ]
            
            self.interactions_sheet.append_row(row_data)
            print("✅ Interaction logged to Google Sheets")
            return True
        
        except Exception as e:
            print(f"❌ Error logging to sheets: {str(e)}")
            return False
    
    async def _get_or_create_contact_by_email(
        self, 
        email: Optional[str], 
        name: str = "Unknown"
    ) -> int:
        """Get existing contact or create new one by email"""
        cursor = self.conn.cursor()
        
        if email:
            cursor.execute("SELECT id FROM contacts WHERE email = ?", (email,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
        
        # Create new contact
        cursor.execute(
            "INSERT INTO contacts (name, email) VALUES (?, ?)",
            (name, email)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    async def get_contact_by_email(self, email: str) -> Optional[Dict]:
        """Get contact details by email"""
        if self.use_google_sheets:
            return await self._get_contact_sheets(email)
        else:
            return await self._get_contact_sqlite(email)
    
    async def _get_contact_sqlite(self, email: str) -> Optional[Dict]:
        """Get contact from SQLite"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contacts WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    async def _get_contact_sheets(self, email: str) -> Optional[Dict]:
        """Get contact from Google Sheets"""
        try:
            cell = self.contacts_sheet.find(email)
            if cell:
                row_data = self.contacts_sheet.row_values(cell.row)
                return {
                    'name': row_data[1] if len(row_data) > 1 else None,
                    'email': row_data[2] if len(row_data) > 2 else None,
                    # Add more fields as needed
                }
        except:
            pass
        return None
    
    async def get_contact_interactions(self, contact_id: int, limit: int = 10) -> List[Dict]:
        """Get interaction history for a contact"""
        if self.use_google_sheets:
            return []  # Simplified for sheets
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM interactions
            WHERE contact_id = ?
            ORDER BY date DESC
            LIMIT ?
        """, (contact_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    async def search_contacts(self, query: str) -> List[Dict]:
        """Search contacts by name, email, or company"""
        if self.use_google_sheets:
            return []  # Simplified
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM contacts
            WHERE name LIKE ? OR email LIKE ? OR company LIKE ?
            ORDER BY last_interaction DESC
            LIMIT 20
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        
        return [dict(row) for row in cursor.fetchall()]
    
    async def get_recent_interactions(self, limit: int = 10) -> List[Dict]:
        """Get recent interactions across all contacts"""
        if self.use_google_sheets:
            return []  # Simplified
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                i.*,
                c.name as contact_name,
                c.email as contact_email,
                c.company as contact_company
            FROM interactions i
            JOIN contacts c ON i.contact_id = c.id
            ORDER BY i.date DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    async def get_stats(self) -> Dict:
        """Get CRM statistics"""
        if self.use_google_sheets:
            return {
                "total_contacts": 0,
                "total_interactions": 0,
                "interactions_this_week": 0
            }
        
        cursor = self.conn.cursor()
        
        # Total contacts
        cursor.execute("SELECT COUNT(*) FROM contacts")
        total_contacts = cursor.fetchone()[0]
        
        # Total interactions
        cursor.execute("SELECT COUNT(*) FROM interactions")
        total_interactions = cursor.fetchone()[0]
        
        # This week's interactions
        cursor.execute("""
            SELECT COUNT(*) FROM interactions
            WHERE date >= datetime('now', '-7 days')
        """)
        week_interactions = cursor.fetchone()[0]
        
        return {
            "total_contacts": total_contacts,
            "total_interactions": total_interactions,
            "interactions_this_week": week_interactions
        }
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()
            print("✅ CRM database connection closed")


# Example usage
async def test_crm_service():
    """Test function for CRM service"""
    service = CRMService(use_google_sheets=False)
    
    # Create contact
    contact_id = await service.create_or_update_contact({
        'name': 'John Doe',
        'email': 'john@example.com',
        'company': 'Acme Corp',
        'title': 'CEO',
        'tags': ['vip', 'customer']
    })
    print(f"Contact created with ID: {contact_id}")
    
    # Log interaction
    await service.log_interaction({
        'contact_email': 'john@example.com',
        'contact_name': 'John Doe',
        'type': 'call',
        'duration_seconds': 1800,
        'summary': 'Discussed Q4 strategy',
        'sentiment': 'positive',
        'action_items': [
            {'task': 'Send proposal', 'deadline': '2024-11-15'}
        ]
    })
    
    # Get contact
    contact = await service.get_contact_by_email('john@example.com')
    print("Contact:", contact)
    
    # Get stats
    stats = await service.get_stats()
    print("CRM Stats:", stats)
    
    service.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_crm_service())