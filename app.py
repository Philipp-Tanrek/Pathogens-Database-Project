import pymysql
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
from flask_mysqldb import MySQL
from flask import request
import re
from flask import Flask, jsonify


###Connect to data base 
db = SQLAlchemy()

# create the app
app = Flask(__name__, static_folder='static')

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'diarrhea'
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:123456@127.0.0.1/diarrhea"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

mysql = MySQL(app)

# Initialize the app with Flask-SQLAlchemy
db.init_app(app)


def is_genebank(s):
    # Regular expressions for GenBank ID patterns
    genbank_patterns = [r'^[A-Z]{1,2}_?\d{6,}$', r'^\d+$']
    if any(re.match(pattern, s) for pattern in genbank_patterns):
        return True
    else:
        return False


def is_uniprot(s):
    # Regular expressions for UniProt and GenBank IDs
    uniprot_patterns = [r'^[A-NR-Z0-9]{6}$', r'^[A-NR-Z0-9]{10}$', r'^[A-Z0-9]+_[A-Z0-9]+$']
    
    if any(re.match(pattern, s) for pattern in uniprot_patterns):
        return True
    else:
        return False


@app.template_filter('getattr')
def getattr_filter(obj, attr):
    return getattr(obj, attr, None)

#Homepage
@app.route('/')
def index():
    return render_template('index.html')


# Pathogens Page
@app.route('/pathogens', methods=['GET', 'POST'])
def pathogens():
    try:
        search_query = request.args.get('search', '').strip()
        cur = mysql.connection.cursor()
        if search_query:
            query = f"SELECT * FROM pathogens WHERE organism LIKE '%{search_query}%' ORDER BY pathogens.id"
        else:
            query = "SELECT * FROM pathogens ORDER BY pathogens.id"
        cur.execute(query)
        data = cur.fetchall()
        return render_template('pathogens.html', data=data)
    except Exception as e:
        return render_template('error.html', error=str(e))

# Proteins associated with a pathogen
@app.route('/pathogen/<int:pathogen_id>/proteins')
def proteins_by_pathogen(pathogen_id):
    try:
        cur = mysql.connection.cursor()
        query = f'''SELECT proteins.id, proteins.protein_name, proteins.uniprot_id 
                    FROM proteins 
                    WHERE proteins.organism_id = {pathogen_id}'''
        cur.execute(query)
        data = cur.fetchall()
        return render_template('proteins2.html', table_name='Proteins for Pathogen', columns=['Protein Name', 'UniProt ID'], data=data)
    except Exception as e:
        return render_template('error.html', error=str(e))

# Proteins Page
@app.route('/proteins', methods=['GET', 'POST'])
def proteins():
    try:
        # Get the search query
        search_query = request.args.get('search', '').strip()

        # Safely get the current page and rows per page from query parameters
        page = request.args.get('page', '1')
        rows_per_page = request.args.get('rows', '20')

        # Validate and convert query parameters to integers with defaults
        try:
            page = int(page) if page.isdigit() and int(page) > 0 else 1
        except ValueError:
            page = 1  # Default to page 1 if invalid

        try:
            rows_per_page = int(rows_per_page) if rows_per_page.isdigit() and int(rows_per_page) > 0 else 20
        except ValueError:
            rows_per_page = 20  # Default to 20 rows if invalid

        # Query to get the total count of proteins
        cur = mysql.connection.cursor()
        count_query = '''SELECT COUNT(*) FROM proteins INNER JOIN pathogens ON proteins.organism_id = pathogens.id'''
        cur.execute(count_query)
        total_count = cur.fetchone()[0]

        # Query to fetch the proteins with pagination
        offset = (page - 1) * rows_per_page
        if search_query:
            query = f'''SELECT proteins.id, proteins.protein_name, proteins.uniprot_id, pathogens.organism 
                        FROM proteins 
                        INNER JOIN pathogens ON proteins.organism_id = pathogens.id 
                        WHERE proteins.protein_name LIKE '%{search_query}%' 
                        ORDER BY proteins.id LIMIT {rows_per_page} OFFSET {offset}'''
        else:
            query = f'''SELECT proteins.id, proteins.protein_name, proteins.uniprot_id, pathogens.organism 
                        FROM proteins 
                        INNER JOIN pathogens ON proteins.organism_id = pathogens.id 
                        ORDER BY proteins.id LIMIT {rows_per_page} OFFSET {offset}'''
        
        cur.execute(query)
        data = cur.fetchall()

        # Calculate the total pages
        total_pages = (total_count // rows_per_page) + (1 if total_count % rows_per_page != 0 else 0)

        # Get protein data for the pie chart
        query_chart = '''SELECT pathogens.organism, COUNT(proteins.id) 
                         FROM proteins 
                         INNER JOIN pathogens ON proteins.organism_id = pathogens.id 
                         GROUP BY pathogens.organism'''
        cur.execute(query_chart)
        protein_data = cur.fetchall()

        return render_template(
            'proteins.html',
            data=data,
            protein_data=protein_data,
            current_page=page,
            total_pages=total_pages,
            rows_per_page=rows_per_page
        )
    except Exception as e:
        return render_template('error.html', error=str(e))



# Domains associated with a protein
@app.route('/protein/<int:protein_id>/domains')
def domains_by_protein(protein_id):
    try:
        cur = mysql.connection.cursor()
        query = f'''SELECT domains.id, domains.domain_name 
                    FROM domains 
                    INNER JOIN protein_domain_mapping ON protein_domain_mapping.domain_id = domains.id 
                    WHERE protein_domain_mapping.protein_id = {protein_id}'''
        cur.execute(query)
        data = cur.fetchall()
        return render_template('domains.html', table_name='Domains for Protein', columns=['Domain Name'], data=data)
    except Exception as e:
        return render_template('error.html', error=str(e))


#Domains Page
@app.route('/domains')
def domains():
    try:
        cur = mysql.connection.cursor()
        query = '''SELECT domains.id, domains.domain_name FROM domains'''
        cur.execute(query)
        data = cur.fetchall()
        #data = db.session.execute(db.select(Domains).order_by(Domains.domain_name)).scalars()
        return render_template('domains.html', table_name='Domains', columns=['Domain Name'], data=data)
    except Exception as e:
        return render_template('error.html', error=str(e))


#Motifs Page
@app.route('/motifs')
def motifs():
    try:
        cur = mysql.connection.cursor()
        query = '''SELECT motifs.id, motifs.motif, domains.domain_name FROM motifs 
        inner join domains
        on motifs.domain_id = domains.id 
        order by motifs.id'''
        cur.execute(query)
        data = cur.fetchall()
        #data = db.session.execute(db.select(Motifs).order_by(Motifs.motif)).scalars()
        return render_template('motifs.html', table_name='Motifs', columns=['Motif', 'Domain ID'], data=data)
    except Exception as e:
        return render_template('error.html', error=str(e))


#Diseases Page
@app.route('/diseases')
def diseases():
    try:
        cur = mysql.connection.cursor()
        query = '''SELECT diseases.id, diseases.diseases_name, pathogens.organism FROM diseases 
        inner join pathogens
        on diseases.pathogen_id = pathogens.id 
        order by diseases.id'''
        cur.execute(query)
        data = cur.fetchall()
        #data = db.session.execute(db.select(Diseases).order_by(Diseases.diseases_name)).scalars()
        return render_template('diseases.html', table_name='Diseases', columns=['Disease Name', 'Pathogen ID'], data=data)
    except Exception as e:
        return render_template('error.html', error=str(e))


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
#########                 API START                ################################################################################################################


@app.route('/data/table/<table_name>', methods=['GET'])
def get_table(table_name):
    cur = mysql.connection.cursor()
    query = f'''SELECT * FROM {table_name}'''
    cur.execute(query)
    data = cur.fetchall()
    cur.close()
    return jsonify(data)


@app.route('/data/proteins/<org_name>', methods=['GET'])
def prot_from_org(org_name):
    cur = mysql.connection.cursor()
    if is_genebank(org_name):
        query = '''SELECT * FROM pathogens
               INNER JOIN proteins
                   ON pathogens.id = proteins.organism_id
               WHERE pathogens.genebank_id = %s'''
    else:
        query = '''SELECT * FROM pathogens
               INNER JOIN proteins
                   ON pathogens.id = proteins.organism_id
               WHERE pathogens.organism = %s'''
    cur.execute(query, (org_name,))
    data = cur.fetchall()
    cur.close()
    return jsonify(data)


@app.route('/data/domains/<prot_name>', methods=['GET'])
def get_domain_from_prot(prot_name):
    if is_uniprot(prot_name):
        cur = mysql.connection.cursor()
        cur.execute('''SELECT * FROM proteins
                        inner join protein_domain_mapping
                            on proteins.id = protein_domain_mapping.protein_id
                        inner join domains
                            on protein_domain_mapping.domain_id = domains.id
                        where proteins.uniprot_id = %s''', (prot_name,))
        data = cur.fetchall()
        cur.close()
        return jsonify(data)
    else:
        cur = mysql.connection.cursor()
        cur.execute('''SELECT * FROM proteins
                        inner join protein_domain_mapping
                            on proteins.id = protein_domain_mapping.protein_id
                        inner join domains
                            on protein_domain_mapping.domain_id = domains.id
                        where proteins.protein_name = %s''', (prot_name,))
        data = cur.fetchall()
        cur.close()
        return jsonify(data)


@app.route('/data/motif/<domain_name>', methods=['GET'])
def get_motif_from_domain(domain_name):
    cur = mysql.connection.cursor()
    cur.execute(f'''SELECT * FROM domains
                        inner join motifs
                            on domains.id = motifs.domain_id
                        where domains.domain_name = "{domain_name}"''')
    data = cur.fetchall()
    cur.close()
    return jsonify(data)

#So i can just run python.app
if __name__ == '__main__':
    app.run(debug=True)
