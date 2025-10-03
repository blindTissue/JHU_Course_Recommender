"""
Script to fetch course data from JHU SIS API and store it locally.
"""
import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class JHUSISFetcher:
    BASE_URL = "https://sis.jhu.edu/api"

    def __init__(self, api_key: str):
        """
        Initialize the SIS API fetcher.

        Args:
            api_key: Your JHU SIS API key
        """
        self.api_key = api_key
        self.session = requests.Session()

    def get_schools(self) -> List[Dict]:
        """Fetch list of all schools."""
        url = f"{self.BASE_URL}/classes/codes/schools?key={self.api_key}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_terms(self) -> List[Dict]:
        """Fetch list of available terms."""
        url = f"{self.BASE_URL}/classes/codes/terms?key={self.api_key}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_departments(self, school: str) -> List[Dict]:
        """
        Fetch departments for a specific school.

        Args:
            school: School name/code
        """
        url = f"{self.BASE_URL}/classes/codes/departments/{school}?key={self.api_key}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_classes(self, school: str, term: str) -> List[Dict]:
        """
        Fetch all classes for a school in a specific term.

        Args:
            school: School name/code
            term: Term code (e.g., Fall 2024)
        """
        url = f"{self.BASE_URL}/classes/{school}/{term}?key={self.api_key}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_course_details(self, offering_name: str, section_name: str, term: str) -> Dict:
        """
        Fetch detailed course information including description.

        Args:
            offering_name: Course offering name (e.g., "EN.601.220")
            section_name: Section number (e.g., "01")
            term: Term (e.g., "Fall 2024")

        Returns:
            Detailed course information including description
        """
        # Convert offering name format: "EN.601.220" -> "EN601220"
        course_num = offering_name.replace('.', '')
        course_section = f"{course_num}{section_name}"
        url = f"{self.BASE_URL}/classes/{course_section}/{term}?key={self.api_key}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def search_classes(self, **params) -> List[Dict]:
        """
        Advanced search for classes with custom parameters.

        Args:
            **params: Any combination of search parameters (Area, CourseNumber,
                     CourseTitle, Department, Instructor, Term, etc.)
        """
        params['key'] = self.api_key
        url = f"{self.BASE_URL}/classes"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_all_courses(self, schools: Optional[List[str]] = None,
                         terms: Optional[List[str]] = None,
                         output_dir: str = "course_data",
                         fetch_descriptions: bool = True) -> Dict:
        """
        Fetch all courses for specified schools and terms and save to disk.

        Args:
            schools: List of school codes (if None, fetches all schools)
            terms: List of term codes (if None, fetches all available terms)
            output_dir: Directory to store the fetched data
            fetch_descriptions: Whether to fetch detailed descriptions for each course

        Returns:
            Dictionary with statistics about fetched data
        """
        os.makedirs(output_dir, exist_ok=True)

        # Fetch schools and terms if not specified
        if schools is None:
            schools_data = self.get_schools()
            print(f"DEBUG: Schools data sample: {schools_data[:2] if schools_data else 'empty'}")
            schools = [s.get('Name') or s.get('Code') for s in schools_data if isinstance(s, dict)]

        if terms is None:
            terms_data = self.get_terms()
            print(f"DEBUG: Terms data sample: {terms_data[:2] if terms_data else 'empty'}")
            # Filter out None values and extract the proper field
            terms = []
            for t in terms_data:
                if isinstance(t, dict):
                    term_val = t.get('Term') or t.get('TermCode') or t.get('Name') or t.get('Code')
                    if term_val and term_val != 'None':
                        terms.append(term_val)

        all_courses = []
        stats = {
            'schools': len(schools),
            'terms': len(terms),
            'total_courses': 0,
            'courses_with_descriptions': 0,
            'fetch_time': datetime.now().isoformat()
        }

        print(f"Fetching courses for {len(schools)} schools and {len(terms)} terms...")

        for school in schools:
            for term in terms:
                try:
                    print(f"Fetching {school} - {term}...")
                    courses = self.get_classes(school, term)

                    # Fetch detailed descriptions if requested
                    if fetch_descriptions:
                        # Get unique course offerings (descriptions are same across sections)
                        unique_courses = {}
                        for course in courses:
                            offering_name = course.get('OfferingName', '')
                            if offering_name and offering_name not in unique_courses:
                                unique_courses[offering_name] = course

                        print(f"  Fetching descriptions for {len(unique_courses)} unique courses (out of {len(courses)} sections)...")

                        # Fetch details for unique courses
                        course_details_map = {}
                        for i, (offering_name, sample_course) in enumerate(unique_courses.items()):
                            try:
                                section_name = sample_course.get('SectionName', '')
                                if offering_name and section_name:
                                    details = self.get_course_details(offering_name, section_name, term)
                                    # Extract SectionDetails from response
                                    if isinstance(details, list) and len(details) > 0:
                                        detail_data = details[0]
                                        if 'SectionDetails' in detail_data and isinstance(detail_data['SectionDetails'], list):
                                            if len(detail_data['SectionDetails']) > 0:
                                                section_detail = detail_data['SectionDetails'][0]
                                                course_details_map[offering_name] = {
                                                    'Description': section_detail.get('Description', ''),
                                                    'Prerequisites': section_detail.get('Prerequisites', [])
                                                }
                                                stats['courses_with_descriptions'] += 1

                                # Progress indicator
                                if (i + 1) % 50 == 0:
                                    print(f"    Progress: {i + 1}/{len(unique_courses)}")
                            except Exception as e:
                                # Continue even if one course fails
                                pass

                        # Apply details to all sections of each course
                        for course in courses:
                            offering_name = course.get('OfferingName', '')
                            if offering_name in course_details_map:
                                course['Description'] = course_details_map[offering_name]['Description']
                                course['Prerequisites'] = course_details_map[offering_name]['Prerequisites']

                    all_courses.extend(courses)
                    print(f"  Found {len(courses)} courses")
                except Exception as e:
                    print(f"  Error fetching {school}/{term}: {e}")
                    continue

        stats['total_courses'] = len(all_courses)

        # Save all courses to JSON
        output_file = os.path.join(output_dir, f"courses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_courses, f, indent=2, ensure_ascii=False)

        # Save metadata
        metadata_file = os.path.join(output_dir, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)

        print(f"\nFetched {stats['total_courses']} total courses")
        print(f"Data saved to {output_file}")

        return stats


def main():
    """Main execution function."""
    import sys
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    # Get API key from environment variable or command line
    api_key = os.getenv('JHU_SIS_API_KEY')

    if not api_key:
        if len(sys.argv) > 1:
            api_key = sys.argv[1]
        else:
            print("Error: API key required")
            print("Usage: python fetch_courses.py <api_key>")
            print("Or set JHU_SIS_API_KEY environment variable")
            sys.exit(1)

    fetcher = JHUSISFetcher(api_key)

    # First fetch Fall 2025 with descriptions
    print("=" * 60)
    print("PHASE 1: Fetching Fall 2025 with descriptions")
    print("=" * 60)
    stats_with_desc = fetcher.fetch_all_courses(
        terms=['Fall 2025'],
        fetch_descriptions=True,
        output_dir='course_data'
    )

    # Then fetch Spring 2024 to Summer 2025 without descriptions (for course variety)
    print("\n" + "=" * 60)
    print("PHASE 2: Fetching Spring 2024 - Summer 2025 (no descriptions)")
    print("=" * 60)
    stats_no_desc = fetcher.fetch_all_courses(
        terms=['Summer 2025', 'Spring 2025', 'Fall 2024', 'Summer 2024', 'Spring 2024'],
        fetch_descriptions=False,
        output_dir='course_data'
    )

    # Combine stats
    stats = {
        'phase1_with_descriptions': stats_with_desc,
        'phase2_without_descriptions': stats_no_desc,
        'total_courses': stats_with_desc['total_courses'] + stats_no_desc['total_courses']
    }

    print("\nFetch complete!")
    print(f"Statistics: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    main()
